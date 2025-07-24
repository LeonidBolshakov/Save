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

from datetime import date
import time
import re
import requests
import logging

logger = logging.getLogger(__name__)

import yadisk
from yadisk.exceptions import PathNotFoundError, PathExistsError

from SRC.YADISK.yandex_token import YandexOAuth  # Модуль для работы с OAuth
from SRC.GENERAL.constant import Constant as C
from SRC.GENERAL.textmessage import TextMessage as T


class YandexDisk:
    """Класс для работы с файлами (архивами) на Яндекс-Диске"""

    def __init__(
        self,
        port: int,  # Номер порта, заданный в приложении Яндекс
        target_date: date = date.today(),  # Дата для именования
        archive_prefix: str = C.REMOTE_ARCHIVE_PREFIX,  # Префикс имени файла архива
        archive_ext: str = C.ARCHIVE_SUFFIX,  # Расширение файла архива
        archive_path: str = C.REMOTE_ARCHIVE_PATH,  # Каталог архивов на Яндекс-Диске
    ):
        logger.info(T.init_yadisk)

        self.port = port
        self.target_date = target_date
        self.archive_prefix = archive_prefix
        self.archive_ext = archive_ext
        self.archive_path: str = archive_path if archive_path else C.REMOTE_ARCHIVE_PATH
        self.yandex_token: str | None = None
        self.disk = yadisk.YaDisk()

        self.archive_name_format = self.get_archive_name_format()
        self.get_token_for_API()

    def get_archive_name_format(self):
        return C.GENERAL_REMOTE_ARCHIVE_FORMAT.format(
            archive=self.archive_prefix,
            year=self.target_date.year,
            month=self.target_date.month,
            day=self.target_date.day,
            file_num="{file_num}",  # Заполнитель для номера
        )

    def get_token_for_API(self):
        # Получение токена для API
        try:
            logger.info(T.get_token)
            yandex_token = YandexOAuth(port=self.port)
            self.yandex_token = yandex_token.get_access_token()
            if not self.yandex_token:
                logger.critical("")
                raise PermissionError(T.no_valid_token)
            self.disk.token = self.yandex_token
            logger.debug(T.valid_token)
        except Exception as e:
            raise RuntimeError(T.get_token_error.format(e=e)) from e

    def remote_archive_name(self) -> str:
        """
        Генерирует уникальное имя архива на основе существующих файлов
        :return: (str) - Имя архива, сгенерированное по шаблону.
        """
        logger.info(T.archive_name_generation)
        # Вычисляем следующий порядковый номер архива на заданную дату
        next_num = max(self._get_file_nums(), default=0) + 1

        # Формируем имя файла архива в соответствии с шаблоном
        return f"{self.archive_name_format.format(file_num=next_num)}{self.archive_ext}"

    def _get_file_nums(self) -> list[int]:
        """
        Возвращает список номеров файлов на заданную дату в целевой директории
        :return: list[int] - Список номеров файлов архивов на заданную дату
        """
        logger.debug(T.getting_file_numbers.format(archive=self.archive_prefix))

        try:
            # Получаем список элементов в папке архивов
            file_nums = self._list_file_nums()
            logger.debug(T.file_numbers_found.format(file_nums=file_nums))
            return file_nums  # Возвращаем список номеров файлов архивов
        # Создание папки для архивов при необходимости
        except PathNotFoundError:  # Папки с архивами не существует
            logger.info(T.folder_not_found.format(archive_path=self.archive_path))
            self.disk.mkdir(self.archive_path)  # Создаём папку с архивами
            logger.info(T.folder_created.format(archive_path=self.archive_path))
            return []
        except Exception as e:
            raise RuntimeError(T.error_list_files.format(e=e)) from e

    def _list_file_nums(self) -> list[int]:
        file_nums = []
        for item in self.disk.listdir(self.archive_path):
            # Извлекаем номер из имени файла
            if item.name is None:
                logger.info(T.none_element)
                continue
            file_num_str = self._extract_file_num(item.name)

            # Пропускаем если не удалось извлечь
            if file_num_str is None:
                continue

            # Преобразуем в число
            file_nums.append(int(file_num_str))
        return file_nums

    def _extract_file_num(self, filename: str) -> int | None:
        """
        Извлекает номер файла из имени файла с помощью регулярного выражения

        :param: filename: (str) - имя файла
        Returns:
            int: номер файла
            None: если имя не соответствует шаблону
        """
        re_archive_name = self._get_archive_pattern_for_date()
        if match := re.match(re_archive_name, filename):
            return int(match.group("file_num"))
        return None

    def _get_archive_pattern_for_date(self) -> re.Pattern:
        """
        Генерирует регулярное выражение для поиска файлов текущего формата
        с учетом даты и префикса
        :return: re. Pattern Сгенерированное регулярное выражение
        """
        # Формируем фиксированный префикс из общего формата
        prefix = self.archive_name_format.format(
            file_num="",  # Убираем часть с номером файла
        )

        # Экранируем спецсимволы для regex
        escaped_prefix = re.escape(prefix)
        escaped_ext = re.escape(self.archive_ext)

        # Собираем полное регулярное выражение
        return re.compile(
            rf"^{escaped_prefix}(?P<file_num>\d+){escaped_ext}$",
            # (?P<file_num>\d+) - группа file_num для номера файла за дату
            re.IGNORECASE,  # Независимый от регистра поиск
        )

    def write_file(self, local_path: str) -> bool:
        """
        Загружает локальный файл на Яндекс-Диск

        :param local_path: Путь к локальному файлу
        :return: Статус операции (True/False)
        """
        logger.info(T.start_load_file.format(local_path=local_path))

        # Формируем полный путь на Яндекс-Диске
        remote_path = f"{self.remote_archive_name}/{self.remote_archive_name()}"
        try:
            # Загрузка файла
            self._upload_file(local_path, remote_path)

            return True
        # Обработка специфических ошибок API
        except yadisk.exceptions.UnauthorizedError:
            logger.critical("")
            raise PermissionError(T.invalid_token)
        except yadisk.exceptions.PathExistsError:
            raise PathExistsError(T.file_exists.format(remote_path=remote_path))
        except yadisk.exceptions.ForbiddenError:
            logger.critical("")
            raise PermissionError(T.not_enough_rights.format(remote_path=remote_path))
        except Exception as err:
            raise Exception(T.error_load_file.format(err=err)) from err

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Выполняет загрузку файла и логирует время."""
        logger.debug(T.load.format(local_path=local_path, remote_path=remote_path))
        t_start = time.time()
        self.disk.upload(
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
            upload_url, remote_path = self.get_file_download_URL()
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

    def get_file_download_URL(self) -> tuple[str, str]:
        """
        Формирование имени файла архива и url пути загрузки файла на Яндекс-Диск
        :return: tuple[str, str] - (url загрузки файла на Яндекс-Диск, сгенерированное имя файла)
                                    или None при невозможности сгенерировать имя
        """
        # Генерация имени архива и удаленного пути
        archive_name = self.remote_archive_name()
        remote_path = f"{self.archive_path}/{archive_name}"
        logger.debug(T.path_to_cloud.format(remote_path=remote_path))
        upload_url = self._get_upload_url(remote_path)

        logger.debug(T.url_received.format(upload_url=upload_url))
        return upload_url, remote_path

    def _get_upload_url(self, remote_path: str) -> str:
        """Выполняет запрос к API для получения URL загрузки."""
        response = requests.get(
            C.API_YANDEX_LOAD_FILE,
            headers={"Authorization": f"OAuth {self.yandex_token}"},
            params={"path": remote_path, "overwrite": "false"},
        )
        if not response.ok:
            raise RuntimeError(T.error_upload_URL)
        return response.json()["href"]


if __name__ == "__main__":
    # Пример использования
    yandex_disk = YandexDisk(12345)
    print(yandex_disk.write_file("yandex_disk.py"))
