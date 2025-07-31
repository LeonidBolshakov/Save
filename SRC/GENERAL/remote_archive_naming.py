import re
from typing import Protocol, Callable
from datetime import date
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class RemoteArchiveNamingProtokol(Protocol):
    accept_remote_directory_element: Callable[[str], None]
    generate_remote_dir: Callable[[], str]
    generate_remote_path: Callable[[], str]


class RemoteArchiveNaming(RemoteArchiveNamingProtokol):
    """
    Сервис для генерации имён архивных файлов и путей к ним на удалённом (облачном) диске.

    Класс реализует протокол `RemoteArchiveNamingProtokol` и предназначен для:
    - приёма списка имён файлов из облачной директории;
    - анализа существующих имён архивов с учётом текущей даты;
    - генерации уникального имени нового архива;
    - построения имён директории хранения и полного пути к файлу архива.

    Атрибуты:
        target_date (date): Дата, используемая при формировании имён и путей
        remote_archive_prefix (str): Префикс имени архива
        archive_ext (str): Расширение архивного файла
        root_remote_archive_dir (str): Корневая директория архива на облачном диске
        full_remote_archive_dir (str): Полный путь к директории на удалённом диске
        file_nums (list[int]): Список извлечённых номеров файлов за выбранную дату
        archive_name_format (str): Формат имени архива.

    Методы вызываемые из классов работы с облачным диском:
        accept_remote_directory_element(item): Обработка имени файла и извлечение номера.
            Этот метод должен быть ОБЯЗАТЕЛЬНО вызван для каждого элемента директории архива
        generate_remote_dir(): Генерация пути к директории архива.
            Этот метод должен быть вызван для определения/формирования пути к директории архива
        generate_remote_path(): Генерация полного пути к новому архиву.

    Пример использования в:
        SRC\\YADISK\\yandex_disk.py
    """

    def __init__(self):
        variables = EnvironmentVariables()
        self.target_date: date = date.today()  # Дата для наименования файла архива
        self.remote_archive_prefix: str = variables.get_var(
            C.ENV_REMOTE_ARCHIVING_PREFIX, C.REMOTE_ARCHIVE_PREFIX
        )  # Префикс имени файла архива
        self.archive_ext: str = C.ARCHIVE_SUFFIX  # Расширение файла архива
        self.root_remote_archive_dir: str = variables.get_var(
            C.ENV_ROOT_REMOTE_ARCHIVE_DIR, C.ROOT_REMOTE_ARCHIVE_DIR
        )  # Головной каталог архивов на облачном диске
        self.full_remote_archive_dir = ""
        self.file_nums: list[int] = []
        self.archive_name_format = self._get_archive_name_format()

    def _create_remote_name(self) -> str:
        """
        Генерирует уникальное имя архива на основе существующих файлов
        :return: (str) - Имя архива, сгенерированное по шаблону.
        """
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

    def _get_archive_name_format(self) -> str:
        """
            Возвращает формат имени архива
            созданный как конкретизация основного формата заданной датой и префиксом архива.
        :return: (str) - Конкретизированный формат имени архива.
        """
        return C.GENERAL_REMOTE_ARCHIVE_FORMAT.format(
            archive=self.remote_archive_prefix,
            year=str(self.target_date.year),
            month=f"{self.target_date.month:02d}",
            day=f"{self.target_date.day:02d}",
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
        """
        CALLBACK

        Генерирует путь на директорию удалённого диска
        :return: (str) - Полное имя удалённой директории
        """
        children_remote_archive_dir = (
            f"{self.target_date.year}_{self.target_date.month:02d}"
        )
        full_remote_archive_dir = self._create_full_remote_archive_dir(
            C.ROOT_REMOTE_ARCHIVE_DIR, children_remote_archive_dir
        )
        return full_remote_archive_dir

    def _create_full_remote_archive_dir(self, root_dir: str, children_dir: str) -> str:
        self.full_remote_archive_dir = f"{root_dir}/{children_dir}"
        return self.full_remote_archive_dir

    def generate_remote_path(self) -> str:
        """
        CALLBACK

        Формирование пути файла архива на удалённом диске

        :return: str - сгенерированный путь на файл
        """
        remote_path = rf"{self.full_remote_archive_dir}/{self._create_remote_name()}"
        logger.debug(T.path_to_cloud.format(remote_path=remote_path))

        return remote_path
