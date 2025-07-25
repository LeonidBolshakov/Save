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
    PathNotFoundError,
)

from SRC.YADISK.yandex_token import YandexOAuth  # Модуль для работы с OAuth
from SRC.GENERAL.createremotepath import RemotePathProtokol
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T
from SRC.YADISK.yandexconst import YandexConstants as YC


class YandexDisk:
    """Класс для работы с файлами (архивами) на Яндекс-Диске"""

    def __init__(self, port: int, call_back_obj: RemotePathProtokol):
        """
        :param port: (int) Номер порта из описания приложения на Яндекс
        :param call_back_obj: объект класса, удовлетворяющего протоколу:

            class RemotePathProtokol(Protocol):
                accept_remote_directory_element: Callable[[str], None]
                generate_remote_name: Callable[[], str]

                accept_remote_directory_element -   должен вызываться для каждого элемента удалённой директории,
                                                    передавая параметром имя файла элемента
                generate_remote_name            -   вызывается для получения сгенерированного имени удалённого файла
        """

        variables = EnvironmentVariables()

        self.port = port  # generate_remote_name:
        self.call_back_obj = call_back_obj  # Объект с call_back функциями.

        self.yandex_token: str = (
            self.get_token_for_API()
        )  # токен доступа к Яндекс-Диску

        self.ya_disk = self.init_ya_disk(self.yandex_token)  # Яндекс-Диск
        self.remote_dir = (
            self.get_remote_dir()
        )  # Каталог с архивом, расположенным в облаке

    def get_remote_dir(self) -> str:
        remote_dir = C.REMOTE_ARCHIVE_DIR
        try:
            self.ya_disk.listdir(remote_dir, max_items=1, limit=1)
        # Создание папки для архивов при необходимости
        except PathNotFoundError:  # Папки с архивами не существует
            logger.info(T.folder_not_found.format(archive_path=remote_dir))
            self.ya_disk.mkdir(remote_dir)  # Создаём папку с архивами
            logger.info(T.folder_created.format(archive_path=remote_dir))
        except Exception as e:
            raise RuntimeError(T.error_list_files.format(e=e))

        return remote_dir

    def get_token_for_API(self) -> str:
        """
        Получение токена для API
        :return: (str) токен доступа к Яндекс-Диску
        """
        try:
            logger.info(T.get_token)
            yandex_token = YandexOAuth(port=self.port)
            self.yandex_token = yandex_token.get_access_token()
            if not self.yandex_token:
                logger.critical("")
                raise PermissionError(T.no_valid_token)
            logger.debug(T.valid_token)
            return self.yandex_token
        except Exception as e:
            raise PermissionError(T.get_token_error.format(e=e))

    @staticmethod
    def init_ya_disk(yandex_token: str) -> YaDisk:
        try:
            disk = yadisk.YaDisk(token="your_token_here")
            # Проверка доступности диска
            disk.check_token()
            return disk
        except UnauthorizedError:
            raise PermissionError(T.authorization_error.format(e=""))
        except BadRequestError:
            raise PermissionError(T.invalid_request)
        except YaDiskError as e:
            raise RuntimeError(T.error_ya_disk.format(e=e))
        except ConnectionError:
            raise RuntimeError(T.no_internet)
        except Exception as e:
            raise RuntimeError(T.unknown_error.format(e=e))

    def create_remote_name(self, remote_dir) -> str:
        for item in self.ya_disk.listdir(remote_dir):
            self.call_back_obj.accept_remote_directory_element(item.name)

        return self.call_back_obj.generate_remote_name()

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Выполняет загрузку файла и логирует время."""
        logger.debug(T.load.format(local_path=local_path, remote_path=remote_path))
        t_start = time.time()
        self.ya_disk.upload(
            local_path,
            remote_path,
            overwrite=False,
            timeout=120,
            chunk_size=4 * 1024 * 1024,
        )
        during = f"{time.time() - t_start:.2f}"
        logger.info(T.during.format(during=during))

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
        logger.info(T.fast_load.format(local_path=local_path))
        try:
            remote_path = self.get_remote_path()

            upload_url = self._get_upload_url(remote_path)
            logger.debug(T.url_received.format(upload_url=upload_url))
            # Открываем локальный файл в бинарном режиме
            with open(local_path, "rb") as f:
                # Шаг 2: загружаем файл напрямую на полученный URL через HTTP PUT
                logger.info(T.start_fast_load.format(local_path=local_path))
                response = requests.put(upload_url, data=f)

            # Проверка на успешную загрузку (ошибки вызовут исключение)
            response.raise_for_status()
            logger.info(
                T.load_success.format(local_path=local_path, remote_path=remote_path)
            )
            return remote_path

        except Exception as err:
            # Обработка любых исключений при загрузке
            logger.error(T.error_load_file.format(err=err))
            return None

    def get_remote_path(self) -> str:
        """
        Формирование пути файла архива на Яндекс-Диске

        :return: str - сгенерированный путь на файл
        """
        # Генерация имени архива и удаленного пути
        remote_name = self.create_remote_name(self.remote_dir)
        remote_path = f"{self.remote_dir}/{remote_name}"
        logger.debug(T.path_to_cloud.format(remote_path=remote_path))

        return remote_path

    def _get_upload_url(self, remote_path: str) -> str:
        """Выполняет запрос к API для получения URL загрузки."""
        response = requests.get(
            YC.API_YANDEX_LOAD_FILE,
            headers={"Authorization": f"OAuth {self.yandex_token}"},
            params={"path": remote_path, "overwrite": "false"},
        )
        if not response.ok:
            raise RuntimeError(T.error_upload_URL)
        return response.json()["href"]
