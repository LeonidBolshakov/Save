import os
import logging
import hashlib
import requests
from typing import BinaryIO
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)
from yadisk.exceptions import YaDiskError

TESTING = os.getenv("TESTING", "0") == "1"
logger = logging.getLogger(__name__)

from SRC.YADISK.yandexconst import YandexConstants as YC
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT


def _requests_put(url, data, timeout):
    import requests

    return requests.put(url, data=data, timeout=timeout)


class HashMismatchError(Exception):
    """Выбрасывается при несовпадении контрольных сумм после загрузки."""


class UploaderToYaDisk:
    """
    Класс для прямой загрузки файлов на Яндекс-Диск с поддержкой повторных попыток
    при временных ошибках или несоответствии контрольной суммы.

    Основные возможности:
    ---------------------
    - Получение одноразового upload URL перед каждой попыткой загрузки.
    - Отправка файла на Яндекс-Диск через PUT-запрос с использованием requests.
    - Обработка HTTP- и сетевых ошибок с помощью retry-механизма библиотеки tenacity.
    - Проверка целостности загруженного файла (MD5) после каждой успешной отправки.
    - Логирование ключевых этапов загрузки и ошибок.

    Механизм повторных попыток:
    ---------------------------
    Повтор выполняется в случаях:
    - Несовпадение MD5-хэшей локального и удалённого файла (HashMismatchError).
    - HTTP-коды 429 (Too Many Requests) и 5xx (временные ошибки сервера).
    - Сетевые ошибки (таймауты, обрывы соединений и т.п.).
    Остальные ошибки (например, FileNotFoundError) считаются фатальными и не повторяются.

    Параметры:
    ----------
    ya_disk : объект-клиент API Яндекс-Диска
        Экземпляр клиента, предоставляющего методы get_upload_link() и get_meta()
    remote_path : str
        Путь на Яндекс-Диске, куда будет загружен файл.

    Основные методы:
    ----------------
    - write_file_direct(local_path): Загружает файл напрямую с локального пути.
    - calculate_md5(file_path): Вычисляет MD5 локального файла.
    - get_remote_md5_yadisk(remote_path): Получает MD5 загруженного файла с сервера.
    - verify_file_hash(local_file, remote_file): Сравнивает локальный и удалённый MD5.

    Исключения:
    -----------
    - HashMismatchError: Выбрасывается при несовпадении MD5-хэшей.
    - requests.exceptions. RequestException: Любая сетевая или HTTP-ошибка.
    """

    def __init__(self, ya_disk, remote_path: str):
        self.ya_disk = ya_disk
        self.remote_path = remote_path

    @staticmethod
    def _is_retryable_status(code: int) -> bool:
        """
        Определяет необходимость повтора, в зависимости от статуса кода ответа сервера
        :param code: статус кода ответа сервера
        :return: True - нужен повтор, False - не нужен повтор
        """
        if code == 429 or 500 <= code <= 504:
            return True
        return False

    # --- Получить новый upload_url перед каждой попыткой ---
    def _get_upload_url(self) -> str:
        """
        Получает одноразовую ссылку для загрузки на Яндекс-Диск.
        Обрабатывает разные форматы ответа API.
        """
        try:
            res = self.ya_disk.get_upload_link(self.remote_path, overwrite=True)

            # Вариант 1: сразу строка
            if isinstance(res, str):
                return res

            # Вариант 2: dict с ключом 'href'
            if isinstance(res, dict) and "href" in res:
                return res["href"]

            # Вариант 3: объект с атрибутом .href
            href = getattr(res, "href", None)
            if isinstance(href, str) and href:
                return href
        except Exception as e:
            raise YaDiskError from e

        # Если формат неожиданный — записываем в лог и падаем с понятной ошибкой
        logger.error(YT.unknown_error.format(type=f"{type(res)!r}", res=f"{res!r}"))
        raise ValueError(YT.unknown_error.format(type=f"{type(res)!r}", res=f"{res!r}"))

    # --- Фильтр: по каким ошибкам повторяем ---
    @staticmethod
    def _should_retry(exc: BaseException) -> bool:
        """
        Определяет, нужно ли повторить операцию при возникновении исключения.
        Вызывается библиотекой tenacity перед повтором.
        """

        # 1) Наши «ожидаемые» поводы для повтора
        if isinstance(exc, HashMismatchError):
            return True

        # 2) Сетевая ошибка
        if isinstance(exc, requests.exceptions.RequestException):

            resp = getattr(exc, "response", None)
            if resp is not None and resp.status_code is not None:
                return UploaderToYaDisk._is_retryable_status(resp.status_code)

            return True  # нет ответа (timeout/connect error) — повторяем

        # 3) По умолчанию — не повторяем (например, FileNotFoundError и пр.)
        return False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception(_should_retry),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True,
    )
    def write_file_direct(self, local_path: str) -> None:
        """
        Загружает локальный файл на Яндекс-Диск напрямую (без chunk-режима).
        """

        # 1) Открываем локальный файл
        with self._open_local_file(path=local_path) as f:
            logger.info(YT.start_fast_load.format(local_path=local_path))

            # 2) На КАЖДОЙ попытке берём новый upload_url
            upload_url = self._get_upload_url()

            # 3) Загрузка файла с таймаутом
            self._put_file(upload_url=upload_url, f=f, timeout=YC.TIME_OUT_SECONDS)

        # 4) Контроль целостности (MD5 локальный vs MD5 из метаданных Яндекс-Диска)
        self._verify_integrity(local_path=local_path, remote_path=self.remote_path)
        # 5) Успех
        logger.info(
            YT.finish_load.format(local_path=local_path, remote_path=self.remote_path)
        )

    @staticmethod
    def _open_local_file(path: str) -> BinaryIO:
        """
        Открываем локальный файл.
        Если файл не найден выбрасываем исключение FileNotFoundError (фатальная ошибка — без повтора)
        :param path: Путь на локальный файл
        :return: Открытый локальный файл
        """
        try:
            return open(path, "rb")
        except FileNotFoundError:
            logger.error(YT.local_file_not_found.format(path=path))
            raise  # tenacity не будет повторять (см. _should_retry)

    def _put_file(self, upload_url: str, f: BinaryIO, timeout: int) -> None:
        """
        Отправка файла в облако
        :param upload_url: URL для загрузки файла
        :param f: Загружаемый файл
        :param timeout: Тайм аут в секундах
        :return: ответ сервера
        """
        if TESTING:
            # имитация успешной отправки
            return

        try:
            resp = _requests_put(upload_url, data=f, timeout=timeout)
            self._raise_for_bad_status(resp)
            return
        except requests.exceptions.RequestException as e:
            logger.info(YT.error_network.format(e=e))
            raise  # tenacity поймает и решит, повторять ли

    @staticmethod
    def _raise_for_bad_status(resp: requests.Response) -> None:
        """
        Проверка на плохой статус ответа на запрос, при необходимости, выброс исключения
        :param resp: ответ на запрос
        :return: None
        """
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Подмешаем response, чтобы фильтр видел status_code
            e.response = resp
            raise

    def _verify_integrity(self, local_path: str, remote_path: str) -> None:
        """
        MD5-проверка локального и записанного в облако файлов и, при необходимости, выброс HashMismatchError.
        :param local_path: Путь на локальный файл.
        :param remote_path: Путь на записанный в облако файл.
        :return:
        """
        if (
                not self.calculate_md5(local_path).lower()
                    == (self.get_remote_md5_yadisk(remote_path) or "").lower()
        ):
            logger.info(YT.mismatch_MD5.format(remote_path=remote_path))
            raise HashMismatchError

    @staticmethod
    def calculate_md5(file_path: str, chunk_size: int = YC.CHUNK_SIZE) -> str:
        """Вычисляет MD5-хэш файла (по частям)."""

        h = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_remote_md5_yadisk(self, remote_path: str) -> str | None:
        """Получает MD5 загруженного файла с Яндекс-Диска (если доступно)."""
        meta = self.ya_disk.get_meta(remote_path, fields="md5")
        if hasattr(meta, "md5"):
            return getattr(meta, "md5")
        if isinstance(meta, dict):
            return meta.get("md5")
        return None
