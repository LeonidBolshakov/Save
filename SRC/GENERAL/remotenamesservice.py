import re
from typing import Protocol, Callable
from datetime import date
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class RemoteNameServiceProtokol(Protocol):
    accept_remote_directory_element: Callable[[str], None]
    generate_remote_dir: Callable[[], str]
    generate_remote_path: Callable[[], str]


class RemoteNamesService(RemoteNameServiceProtokol):
    def __init__(self):
        self.target_date: date = date.today()  # Дата для наименования
        self.archive_prefix: str = C.REMOTE_ARCHIVE_PREFIX  # Префикс имени файла архива
        self.archive_ext: str = C.ARCHIVE_SUFFIX  # Расширение файла архива
        self.remote_archive_dir: str = (
            C.REMOTE_ARCHIVE_DIR
        )  # Каталог архивов на облачном диске
        self.file_nums: list[int] = []
        self.archive_name_format = self.get_archive_name_format()

    def create_remote_name(self) -> str:
        """
        CALLBACK

        Генерирует уникальное имя архива на основе существующих файлов
        :return: (str) - Имя архива, сгенерированное по шаблону.
        """
        # Получаем список элементов в папке архивов
        logger.debug(T.file_numbers_found.format(file_nums=self.file_nums))
        logger.info(T.archive_name_generation)
        # Вычисляем следующий порядковый номер архива на заданную дату
        next_num: int = max(self.file_nums, default=0) + 1

        # Формируем имя файла архива в соответствии с шаблоном
        return f"{self.archive_name_format.format(file_num=next_num)}{self.archive_ext}"

    def accept_remote_directory_element(self, item: str) -> None:
        """
        CALLBACK

        Получает очередное имя файла из каталога и формирует список имён файлов, прошедших фильтрацию
        :param item: (str) Имя очередного файла
        :return: None
        """
        if item is None:
            logger.info(T.none_element)
            return

        # Извлекаем номер файла из имени файла
        file_num_str = self._extract_file_num(item)

        # Пропускаем если не удалось извлечь
        if file_num_str is None:
            return

        # Преобразуем в число и сохраняем
        self.file_nums.append(int(file_num_str))
        return

    def get_archive_name_format(self):
        return C.GENERAL_REMOTE_ARCHIVE_FORMAT.format(
            archive=self.archive_prefix,
            year=self.target_date.year,
            month=self.target_date.month,
            day=self.target_date.day,
            file_num="{file_num}",  # Заполнитель для номера
        )

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

    def generate_remote_dir(self) -> str:
        return self.remote_archive_dir

    def generate_remote_path(self) -> str:
        """
        Формирование пути файла архива на Яндекс-Диске

        :return: str - сгенерированный путь на файл
        """
        # Генерация имени архива и удаленного пути
        remote_path = f"{self.remote_archive_dir}/{self.create_remote_name()}"
        logger.debug(T.path_to_cloud.format(remote_path=remote_path))

        return remote_path
