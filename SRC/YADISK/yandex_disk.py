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
import requests
import logging

logger = logging.getLogger(__name__)

import yadisk
from yadisk import YaDisk
from yadisk.exceptions import (
    YaDiskError,
    UnauthorizedError,
    BadRequestError,
)

from SRC.YADISK.OAUTH.yandexoauth import OAuthFlow  # Модуль для работы с OAuth
from SRC.GENERAL.remote_archive_naming import RemoteArchiveNamingProtokol
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT
from SRC.YADISK.yandexconst import YandexConstants as YC


class YandexDisk:
    """Класс для работы с файлами (архивами) на Яндекс-Диске"""

    def __init__(self, remote_dir: str, call_back_obj: RemoteArchiveNamingProtokol):
        """
        :param remote_dir: (str) Директория на Яндекс-Диске с архивами
        :param call_back_obj: объект класса, удовлетворяющего протоколу:

            class RemoteArchiveNamingProtokol:

                accept_remote_directory_element: Callable[[str], None]
                generate_remote_name: Callable[[], str]

                accept_remote_directory_element -   должен вызываться для каждого элемента удалённой директории,
                                                    передавая параметром имя файла элемента
                generate_remote_dir             -   возвращает сгенерированный путь на удалённую директорию.
                generate_remote_path            -   возвращает сгенерированный путь удалённого файла
        """

        variables = EnvironmentVariables()

        self.call_back_obj = call_back_obj  # Объект с call_back функциями.
        self.remote_path: str = ""

        self.access_token: str | None = (
            self.get_token_for_API()
        )  # токен доступа к Яндекс-Диску

        self.ya_disk = self.init_ya_disk(self.access_token)
        # Яндекс-Диск
        self.remote_dir = self.create_remote_dir()

    def create_remote_dir(self) -> str:
        # CALLBACK
        remote_dir = self.call_back_obj.generate_remote_dir()
        if not self.ya_disk.exists(remote_dir):
            logger.info(YT.folder_not_found.format(archive_path=remote_dir))
            try:
                current_path = self.mkdir_custom(remote_dir)  # Создаём папку с архивами
                logger.info(YT.folder_created.format(archive_path=current_path))
            except Exception as e:
                raise YaDiskError(YT.error_create_directory_ya_disk.format(e=e))
        return remote_dir

    def get_token_for_API(self) -> str:
        """
        Получение токена для API
        :return: (str) токен доступа к Яндекс-Диску
        """
        try:
            logger.info(YT.get_token)
            self.access_token = OAuthFlow().get_access_token()
            if not self.access_token:
                logger.critical("")
                raise PermissionError(YT.no_valid_token)
            logger.debug(YT.valid_token)
            return self.access_token
        except Exception as e:
            raise PermissionError(YT.get_token_error.format(e=e)) from e

    @staticmethod
    def init_ya_disk(access_token: str) -> YaDisk:
        try:
            disk = yadisk.YaDisk(token=access_token)
            # Проверка доступности диска
            if disk.check_token(token=access_token):
                return disk
            raise PermissionError(YT.authorization_error.format(e=""))
        except UnauthorizedError as e:
            raise PermissionError(YT.authorization_error.format(e="")) from e
        except BadRequestError as e:
            raise PermissionError(YT.invalid_request) from e
        except YaDiskError as e:
            raise RuntimeError(YT.error_ya_disk.format(e=e)) from e
        except ConnectionError as e:
            raise RuntimeError(YT.no_internet) from e
        except Exception as e:
            raise RuntimeError(YT.unknown_error.format(e=e)) from e

    def create_remote_path(self) -> str:
        for item in self.ya_disk.listdir(self.remote_dir):
            if item is not None and item.name is not None:
                # CALLBACK
                self.call_back_obj.accept_remote_directory_element(item.name)

        # CALLBACK
        return self.call_back_obj.generate_remote_path()

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Выполняет загрузку файла и логирует время."""
        logger.debug(YT.load.format(local_path=local_path, remote_path=remote_path))
        t_start = time.time()
        self.ya_disk.upload(
            local_path,
            remote_path,
            overwrite=False,
            timeout=120,
            chunk_size=4 * 1024 * 1024,
        )
        during = f"{time.time() - t_start:.2f}"
        logger.info(YT.during.format(during=during))

    def write_file_fast(self, local_path: str) -> str | None:
        """
        Быстрая загрузка файла на Яндекс-Диск через прямой REST API.

        Метод использует двухэтапную загрузку:
        1. Получает уникальный URL для загрузки от Яндекс-Диска (через API).
        2. Загружает файл напрямую по этому URL с помощью HTTP PUT.

        Этот способ обеспечивает максимальную производительность, сопоставимую
        с загрузкой через веб-интерфейс, в отличие от стандартного метода через yadisk.

        Args:
            local_path (str): Путь к локальному файлу, который нужно загрузить.

        Returns:
            bool: путь на архив на целевом (облачном) диске, если загрузка прошла успешно, иначе None.

        Raises:
            Непосредственно не выбрасывает исключения наружу, но печатает ошибки,
            возникшие при получении URL или при самой загрузке файла.
        """
        logger.info(YT.fast_load.format(local_path=local_path))
        try:
            self.remote_path = self.create_remote_path()

            upload_url = self._get_upload_url(self.remote_path)
            logger.debug(YT.url_received.format(upload_url=upload_url))
            # Открываем локальный файл в бинарном режиме
            with open(local_path, "rb") as f:
                # Шаг 2: загружаем файл напрямую на полученный URL через HTTP PUT
                logger.info(YT.start_fast_load.format(local_path=local_path))
                response = requests.put(upload_url, data=f)

            # Проверка на успешную загрузку (ошибки вызовут исключение)
            response.raise_for_status()
            logger.info(
                YT.load_success.format(
                    local_path=local_path, remote_path=self.remote_path
                )
            )
            return self.remote_path

        except Exception as err:
            # Обработка любых исключений при загрузке
            logger.error(YT.error_load_file.format(err=err))
            return None

    def _get_upload_url(self, remote_path: str) -> str:
        """Выполняет запрос к API для получения URL загрузки."""
        response = requests.get(
            YC.API_YANDEX_LOAD_FILE,
            headers={"Authorization": f"OAuth {self.access_token}"},
            params={"path": remote_path, "overwrite": "false"},
        )
        if not response.ok:
            raise RuntimeError(YT.error_upload_URL)
        return response.json()["href"]

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
            raise YaDiskError(YT.error_create_directory_ya_disk.format(e=e)) from e
