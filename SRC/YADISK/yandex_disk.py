"""
Модуль для работы с. Яндекс-Диском
Обеспечивает загрузку архивов с автоматическим именованием
и проверкой существующих файлов.

Основной класс:
- YandexDisk: Управление загрузкой архивов

Особенности:
- Проверка валидности токена перед загрузкой
- Обработка специфических ошибок API
- Автоматическое создание папки для архивов
- Подробное логирование операций
"""

import time
import os
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from yadisk import YaDisk
from yadisk.sessions.requests_session import RequestsSession
from yadisk.exceptions import (
    YaDiskError,
    UnauthorizedError,
    BadRequestError,
)

from SRC.GENERAL.remote_archive_naming import RemoteArchiveNamingProtokol
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT
from SRC.YADISK.yandexconst import YandexConstants as YC

from SRC.YADISK.uploader_yadisk import UploaderToYaDisk

TESTING = os.getenv("TESTING", "0") == "1"

logger = logging.getLogger(__name__)


# noinspection PyMethodMayBeStatic
class _Client:
    def __init__(self, token=None):
        self._token = token

    # у реального API сигнатура check_token(token=None)
    def check_token(self, token=None):
        return True

    def exists(self, path: str) -> bool:
        return True

    def mkdir(self, path: str) -> None:
        return None

    def get_meta(self, path: str, fields: str | None = None):
        # объект с атрибутом md5
        return type("M", (), {"md5": "0" * 32})()

    def get_upload_link(self, path: str):
        # форма, совместимая с реальным API
        return {"href": "http://dummy"}

    def upload(self, local_path: str, remote_path: str, overwrite: bool = True):
        # безопасный no operation для тестов
        return None


def get_oauth_flow():
    from SRC.YADISK.OAUTH.oauthflow import OAuthFlow

    return OAuthFlow()


def get_token():
    flow = get_oauth_flow()
    token = flow.get_access_token()
    if not token:
        # тот же текст, что использовался ниже
        raise PermissionError(YT.no_valid_token)
    return token


class YandexDisk:
    """Класс для работы с файлами (архивами) на Яндекс-Диске"""

    def __init__(self, remote_dir: str, call_back_obj: RemoteArchiveNamingProtokol):
        """
        :param remote_dir: (str) Директория на Яндекс-Диске с архивами
        :param call_back_obj: объект класса, удовлетворяющего протоколу:

            class RemoteArchiveNamingProtokol:

                accept_remote_directory_element: Callable[[str], None]
                generate_path_remote_dir: Callable[[], str]
                generate_path_remote_file: Callable[[], str]

                accept_remote_directory_element -   должен вызываться для каждого элемента удалённой директории,
                                                    передавая параметром имя файла элемента
                generate_path_remote_dir             -   возвращает сгенерированный путь на удалённую директорию.
                generate_path_remote_file            -   возвращает сгенерированный путь удалённого файла
        """

        self.call_back_obj = call_back_obj  # Объект с call_back функциями.
        self.remote_path: str = ""

        self.access_token: str | None = (
            self.get_token_for_API()
        )  # токен доступа к Яндекс-Диску

        self.ya_disk = self.init_ya_disk(self.access_token)

        self.remote_dir = self.create_remote_dir()

    @staticmethod
    def _get_ya_disk(access_token: str) -> YaDiskError:
        import yadisk

        try:
            session = RequestsSession()
            disk = yadisk.YaDisk(token=access_token, session=session)
            # Проверка доступности диска
            if disk.check_token():
                return disk
            logger.info(YT.authorization_error.format(e=""))
            raise PermissionError
        except UnauthorizedError as e:
            logger.error(YT.authorization_error.format(e=e))
            raise PermissionError from e
        except BadRequestError as e:
            logger.error(YT.invalid_request)
            raise PermissionError from e
        except YaDiskError as e:
            logger.error(YT.error_ya_disk.format(e=e))
            raise RuntimeError from e
        except ConnectionError as e:
            logger.error((YT.no_internet.format(e=e)))
            raise RuntimeError from e
        except Exception as e:
            logger.error(YT.unknown_error.format(e=e))
            raise RuntimeError from e

    def create_remote_dir(self) -> str:
        try:
            # CALLBACK
            remote_dir = self.call_back_obj.generate_path_remote_dir()
            if not self.ya_disk.exists(remote_dir):
                logger.info(YT.folder_not_found.format(remote_dir=remote_dir))
                current_path = self.mkdir_custom(remote_dir)  # Создаём папку с архивами
                logger.info(YT.folder_created.format(current_path=current_path))
            return remote_dir
        except Exception as e:
            raise YaDiskError(YT.error_create_directory_ya_disk.format(e=e))

    def get_token_for_API(self) -> str:
        """
        Получение токена для API
        :return: (str) токен доступа к Яндекс-Диску
        """
        try:
            logger.info(YT.get_token)
            self.access_token = get_token()
            logger.debug(YT.valid_token)
            return self.access_token
        except Exception as e:
            raise PermissionError(YT.get_token_error.format(e=e)) from e

    def init_ya_disk(self, access_token: str) -> YaDisk:
        if TESTING:
            return _Client(access_token)  # без сети в тестах
        return self._get_ya_disk(access_token)

    def create_remote_path(self) -> str:
        for item in self.ya_disk.listdir(self.remote_dir):
            if item is not None and item.name is not None:
                # CALLBACK
                self.call_back_obj.accept_remote_directory_element(item.name)

        # CALLBACK
        return self.call_back_obj.generate_path_remote_file()

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Выполняет загрузку файла и логирует время (через high-level API yadisk)."""
        logger.debug(YT.load.format(local_path=local_path, remote_path=remote_path))
        t_start = time.time()
        self.ya_disk.upload(
            local_path,
            remote_path,
            overwrite=False,
            timeout=YC.TIME_OUT_SECONDS,
            chunk_size=YC.CHUNK_SIZE,
        )
        during = f"{time.time() - t_start:.2f}"
        logger.info(YT.during.format(during=during))

    def write_file_fast(self, local_path: str) -> str | None:
        """
        Быстрая загрузка файла на Яндекс-Диск через прямой REST API.

        Метод использует двухэтапную загрузку:
        1) формирует целевой удалённый путь;
        2) делегирует загрузку `UploaderToYaDisk`, который на каждой попытке
           сам получает одноразовый upload_url и загружает файл с повторами/таймаутами.

        Returns:
            str | None: путь архива на облаке, если загрузка прошла успешно, иначе None.
        """
        logger.info(YT.fast_load.format(local_path=local_path))
        try:
            self.remote_path = self.create_remote_path()

            # Делегируем загрузку: внутри загрузчик сам получит upload_url, сделает повторы и проверит MD5
            uploader = (
                UploaderToYaDisk(  # делегат загрузки (повторы, таймауты, проверку MD5)
                    ya_disk=self.ya_disk, remote_path=self.remote_path
                )
            )
            uploader.write_file_direct(local_path)

            return self.remote_path

        except Exception as err:
            logger.error(YT.error_load_file.format(err=err))
            return None

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            YaDiskError,
        ),
    )
    def mkdir_custom(self, path: str) -> str:
        """
        Рекурсивно создаёт директорию на Яндекс-Диске.

        :param path: Путь, например: "Архивы/2025/08"
        :return: Абсолютный путь, который был создан
        """
        try:
            parts = path.strip("/").split("/")
            current_path = ""
            for part in parts:
                current_path += f"/{part}"
                if not self.ya_disk.exists(current_path):
                    self.ya_disk.mkdir(current_path)
            return current_path

        except Exception as e:
            logger.error(YT.error_create_directory_ya_disk.format(e=e))
            raise YaDiskError from e
