import logging
import hashlib
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log,
)

logger = logging.getLogger(__name__)


class HashMismatchError(Exception):
    """Выбрасывается при несовпадении контрольных сумм после загрузки."""


class UploaderToYaDisk:
    def __init__(self, ya_disk, remote_path: str):
        self.ya_disk = ya_disk
        self.remote_path = remote_path

    # --- Фильтр: по каким ошибкам повторяем ---
    @staticmethod
    def _should_retry(exc: Exception) -> bool:
        # 1) Наши «ожидаемые» поводы для повтора
        if isinstance(exc, HashMismatchError):
            return True

        # 2) Сетевая ошибка requests — да
        if isinstance(exc, requests.exceptions.RequestException):
            resp = getattr(exc, "response", None)

            # Если есть ответ – повторяем 429 и 5xx
            if resp is not None and resp.status_code is not None:
                if resp.status_code == 429 or 500 <= resp.status_code <= 504:
                    return True

            # Если ответа нет (time out, connect error и т.п.) — тоже повторяем
            return True

        # 3) По умолчанию — не повторяем (например, FileNotFoundError и пр.)
        return False

    # --- Получить новый upload_url перед каждой попыткой ---
    def _get_upload_url(self) -> str:
        """
        Возвращает одноразовый upload URL для текущего self.remote_path.
        Поддерживает разные форматы ответа yadisk.get_upload_link(...).
        """
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

        # Если формат неожиданный — записываем в лог и падаем с понятной ошибкой
        logger.error(
            f"Не удалось извлечь upload URL из ответа: {type(res)!r} -> {res!r}"
        )
        raise RuntimeError

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception(_should_retry),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def write_file_direct(self, local_path: str) -> None:
        # 1) Проверим локальный файл (фатальная ошибка — без повтора)
        try:
            f = open(local_path, "rb")
        except FileNotFoundError:
            logger.error("Локальный файл не найден: %s", local_path)
            raise  # tenacity не будет повторять (см. _should_retry)

        with f:
            logger.info("Начинаю быструю загрузку: %s", local_path)

            # 2) На КАЖДОЙ попытке берём новый upload_url
            upload_url = self._get_upload_url()

            # 3) Загрузка с таймаутом
            try:
                resp = requests.put(upload_url, data=f, timeout=60)
                try:
                    resp.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    # Подмешаем response, чтобы фильтр видел status_code
                    e.response = resp
                    raise
            except requests.exceptions.RequestException as e:
                logger.warning("Сетевая ошибка при загрузке: %s", e)
                raise  # поймает tenacity и решит, повторять ли

        # 4) Контроль целостности (MD5 локальный vs MD5 из метаданных Яндекс-Диска)
        if not self.verify_file_hash(local_path, self.remote_path):
            logger.warning(
                "Несовпадение MD5 для %s — попробуем ещё раз", self.remote_path
            )
            raise HashMismatchError(f"MD5 mismatch for {self.remote_path}")

        # 5) Успех
        logger.info("Загрузка завершена: %s → %s", local_path, self.remote_path)

    @staticmethod
    def calculate_md5(file_path: str, chunk_size: int = 64 * 1024) -> str:
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()

    def get_remote_md5_yadisk(self, remote_path: str):
        meta = self.ya_disk.get_meta(remote_path, fields="md5")
        if hasattr(meta, "md5"):
            return getattr(meta, "md5")
        if isinstance(meta, dict):
            return meta.get("md5")
        return None

    def verify_file_hash(self, local_file: str, remote_file: str) -> bool:
        return (
            self.calculate_md5(local_file).lower()
            == (self.get_remote_md5_yadisk(remote_file) or "").lower()
        )
