"""
Модуль для работы с. Яндекс-Диском
Обеспечивает загрузку архивов с автоматическим именованием
и проверкой существующих файлов.

Основной класс:
- YandexDisk: Управление загрузкой архивов

Особенности:
- Автоматическая генерация имен файлов по шаблону
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

from SRC.YADISK.yandex_token import YandexOAuth  # Модуль для работы с OAuth
from SRC.GENERAL.remotenameservice import RemoteNameServiceProtokol
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT
from SRC.YADISK.yandexconst import YandexConstants as YC


class YandexDisk:
    """Класс для работы с файлами (архивами) на Яндекс-Диске"""

    def __init__(
        self, port: int, remote_dir: str, call_back_obj: RemoteNameServiceProtokol
    ):
        """
        :param port: (int) Номер порта из описания приложения на Яндекс
        :param remote_dir: (str) Директория на Яндекс-Диске с архивами
        :param call_back_obj: объект класса, удовлетворяющего протоколу:

            class RemoteNameServiceProtokol:

                accept_remote_directory_element: Callable[[str], None]
                generate_remote_name: Callable[[], str]

                accept_remote_directory_element -   должен вызываться для каждого элемента удалённой директории,
                                                    передавая параметром имя файла элемента
                generate_remote_name            -   возвращает сгенерированное имя удалённого файла
        """

        variables = EnvironmentVariables()

        self.port = port  # generate_remote_name:
        self.remote_dir = remote_dir
        self.call_back_obj = call_back_obj  # Объект с call_back функциями.

        self.yandex_token: str | None = (
            self.get_token_for_API()
        )  # токен доступа к Яндекс-Диску

        self.ya_disk = self.init_ya_disk(self.yandex_token)  # Яндекс-Диск
        self.check_remote_dir()

    def check_remote_dir(self) -> None:
        if not self.ya_disk.exists(self.remote_dir):
            logger.info(YT.folder_not_found.format(archive_path=self.remote_dir))
            self.ya_disk.mkdir(self.remote_dir)  # Создаём папку с архивами
            logger.info(YT.folder_created.format(archive_path=self.remote_dir))

    def get_token_for_API(self) -> str:
        """
        Получение токена для API
        :return: (str) токен доступа к Яндекс-Диску
        """
        try:
            logger.info(YT.get_token)
            yandex_token = YandexOAuth(port=self.port)
            self.yandex_token = yandex_token.get_access_token()
            if not self.yandex_token:
                logger.critical("")
                raise PermissionError(YT.no_valid_token)
            logger.debug(YT.valid_token)
            return self.yandex_token
        except Exception as e:
            raise PermissionError(YT.get_token_error.format(e=e))

    @staticmethod
    def init_ya_disk(yandex_token: str) -> YaDisk:
        try:
            disk = yadisk.YaDisk(token=yandex_token)
            # Проверка доступности диска
            if disk.check_token(token=yandex_token):
                return disk
            raise PermissionError(YT.authorization_error.format(e=""))
        except UnauthorizedError:
            raise PermissionError(YT.authorization_error.format(e=""))
        except BadRequestError:
            raise PermissionError(YT.invalid_request)
        except YaDiskError as e:
            raise RuntimeError(YT.error_ya_disk.format(e=e))
        except ConnectionError:
            raise RuntimeError(YT.no_internet)
        except Exception as e:
            raise RuntimeError(YT.unknown_error.format(e=e))

    def create_remote_name(self, remote_dir) -> str:
        for item in self.ya_disk.listdir(remote_dir):
            if item is not None and item.name is not None:
                self.call_back_obj.accept_remote_directory_element(item.name)

        return self.call_back_obj.generate_remote_name()

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
            remote_path = self.get_remote_path()

            upload_url = self._get_upload_url(remote_path)
            logger.debug(YT.url_received.format(upload_url=upload_url))
            # Открываем локальный файл в бинарном режиме
            with open(local_path, "rb") as f:
                # Шаг 2: загружаем файл напрямую на полученный URL через HTTP PUT
                logger.info(YT.start_fast_load.format(local_path=local_path))
                response = requests.put(upload_url, data=f)

            # Проверка на успешную загрузку (ошибки вызовут исключение)
            response.raise_for_status()
            logger.info(
                YT.load_success.format(local_path=local_path, remote_path=remote_path)
            )
            return remote_path

        except Exception as err:
            # Обработка любых исключений при загрузке
            logger.error(YT.error_load_file.format(err=err))
            return None

    def get_remote_path(self) -> str:
        """
        Формирование пути файла архива на Яндекс-Диске

        :return: str - сгенерированный путь на файл
        """
        # Генерация имени архива и удаленного пути
        remote_name = self.create_remote_name(self.remote_dir)
        remote_path = f"{self.remote_dir}/{remote_name}"
        logger.debug(YT.path_to_cloud.format(remote_path=remote_path))

        return remote_path

    def _get_upload_url(self, remote_path: str) -> str:
        """Выполняет запрос к API для получения URL загрузки."""
        response = requests.get(
            YC.API_YANDEX_LOAD_FILE,
            headers={"Authorization": f"OAuth {self.yandex_token}"},
            params={"path": remote_path, "overwrite": "false"},
        )
        if not response.ok:
            raise RuntimeError(YT.error_upload_URL)
        return response.json()["href"]
