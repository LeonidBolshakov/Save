from abc import ABC, abstractmethod
import subprocess
from pathlib import Path
from typing import Protocol, Callable
import sys
import logging

from mypy.checkpattern import self_match_type_names

logger = logging.getLogger(__name__)  # Используем логгер по имени модуля

from password_strength import PasswordStats

from SRC.GENERAL.textmessage import TextMessage as T


class BacupManagerArchiver(Protocol):
    create_archive: Callable[[], str | None]


class Archiver(ABC, BacupManagerArchiver):
    """
    Архиватор - Класс для создания архивов.

    Специфика архива:
    1. Пути архивируемых файлов записаны строками в файле.
    2. Поддерживает шифрование паролем и защиту имен файлов.

    Использует следующие parameters_dict ключи (включая базовый класс) :
        Archiver: - Дочерний класс архиватора. Например, Archiver7z
        SearchProgramme: - Дочерний класс для поиска программы. Например, SearchProgramme7Z
        archive_extension: str - Расширение архива. Например, '.exe'
        archiver_name: str - Шаблон имени программы
        archiver_standard_program_paths: list[str] - Стандартные пути программы (Опционально)
        compression_level: int Уровень сжатия  (опционально) [0, 9].
                0- без сжатия, 9 - ультра сжатие
        config_file_path: str - Путь на файл конфигурации с путями программ
        list_archive_file_paths: str - Путь на файл, содержащий архивируемые файлы
        local_archive_name: str - Имя локального архива
        password: str - Пароль (опционально)
    """

    def __init__(
        self,
        parameters_dict: dict,
    ) -> None:
        """
        Инициализирует экземпляр класса.

        Args:
            parameters_dict: dict. Словарь параметров

        Raises:
            ValueError: Если не указан путь к архиву
            FileExistsError: Если по указанному пути архива уже существует файл/директория с именем архива
            ValueError: Если архив имеет неверное расширение (не .exe)
            FileNotFoundError: Если файл со списком архивируемых файлов не существует
        """

        self.parameters_dict = parameters_dict
        self.SearchProgramme = parameters_dict["SearchProgramme"]

    def create_archive(self) -> str | None:
        """
        Выполняет создание архива.
        Этот метод использует BackupManager(ABC)

        Process:
        1. Формирует команду архивации
        2. Выполняет команду через subprocess
        3. Обрабатывает результаты выполнения

        Parameters:
            self

        Used parameters_dict keys:
            archive_path: str - Полный путь создаваемого архива
            list_file: str - Полный путь на файл, содержащий имена архивируемых файлов
            password: str | None = None - Пароль. Если пароль на задан файл не архивируется
            0 - нет компрессии, 9 - ультра компрессия

        Returns:
            str | None:Путь на архив или None

        Raises:
            RunTimeError: При провале архивации или завершении архивации с фатальными ошибками

        Note:
            Для Windows используется кодировка cp866 для корректного отображения вывода

        List_file
        текстовый файл содержащий список архивируемых файлов. Допускаются символы подстановки.
        Кодировка файла - utf-8.
        Имена файлов в таком файле списка должны быть разделены символами новой строки.

        Например, если файл "listfile.txt" содержит следующее:

            'My programs/*.cpp'
            'Src/*.cpp'

        То в архив будут добавлены все файлы "*.cpp" из каталогов "My programs" и "Src".
        """
        # Контроль параметров
        logger.debug(T.init_arch)

        # Загрузка параметров
        archive_path = self.get_archive_path()
        self.parameters_dict["archive_path"] = archive_path
        list_archive_file_paths = self.parameters_dict["list_archive_file_paths"]
        password = self.parameters_dict.get("password")

        # Контроль параметров
        self._check_all_params()

        # готовим командную строку для запуска архиватора
        archiver_program = self.get_archiver_program()
        cmd = self._get_cmd_archiver(archiver_program)
        logger.debug(
            T.starting_archiving.format(
                cmd=self._mask_password_in_cmd(cmd=cmd, password=password)
            )
        )

        # Запускаем программу архиватор
        return (  # archive_path было задано как имя архива при формировании cmd
            archive_path
            if self._run_archiver(cmd=cmd, archive_path=archive_path)
            else None
        )

    def _run_archiver(self, cmd: list[str], archive_path: str) -> bool:
        """
        запуск программы архиватора по заранее сформированной разобранной строке

        :param cmd: Список строк, соединив которые, получаем команду для запуска программы архиватора.
        :param archive_path:

        :return: True, если сформирован "хороший" архив, False в противном случае

        :raise: RuntimeError - была критическая ошибка при архивировании
        """
        try:
            process = self._run_archive_process(cmd=cmd)
            if process.returncode == 1:
                logger.warning(process.stderr)
            if process.returncode > 1:
                logger.error(process.stderr)
                return None
            return True
        except Exception as e:
            logger.critical("")
            raise RuntimeError(T.error_starting_archiving.format(e=e))

    def get_archive_path(self) -> str:
        """
        Формирует и возвращает полный путь на архив

        :return: (str) полный путь на архив
        """

        archive_dir = self.parameters_dict["archive_dir"]
        archive_name = self.parameters_dict["local_archive_name"]
        return str(Path(archive_dir, archive_name))

    @abstractmethod
    def _get_cmd_archiver(self, archiver_program: str) -> list[str]:
        pass

    def _check_all_params(self) -> None:
        """
        Выполняет комплексную проверку всех переданных параметров.

        Выполняет следующие проверки:
        1. Корректность пути и имени архива
        2. Наличие и корректность файла со списком файлов

        :Parameters: archive_path - Путь на архив.
        :Parameters: list_file - Путь на файл, содержащий список архивируемых файлов.
            Структура файла списка архивируемых файлов описана.

        Raises:
            Различные исключения в зависимости от типа ошибки
        """
        self._check_arch_exists()
        self._check_list_file()
        self._check_password()

    def _check_arch_exists(self) -> None:
        """
        Проверяет отсутствие файла/директории с заданным именем.

        Args:
            ---

        Raises:
            FileExistsError: Если по указанному пути уже существует файл или директория
        """
        archive_path: str = self.parameters_dict["archive_path"]
        if not Path(archive_path).exists():
            return

        obj_type = "файл" if Path(archive_path).is_file() else "директория"
        raise FileExistsError(
            T.arch_exists.format(obj_type=obj_type, arch_path=archive_path)
        )

    def _check_list_file(self) -> None:
        """
        Проверяет существование файла со списком архивируемых файлов

        :parameter:
            ---

        Raises:
            FileNotFoundError: Если файл со списком не существует
        """
        # Проверяем существует ли список архивируемых файлов
        list_archive_file_paths = self.parameters_dict["list_archive_file_paths"]
        list_file_path = Path(list_archive_file_paths)
        if not list_file_path.exists():
            logger.critical("")
            raise FileNotFoundError(
                T.not_found_list_file_path.format(list_file_path=list_file_path)
            )
        logger.debug(T.exists_list_file.format(list_file_path=list_file_path))

    def _check_password(self) -> None:
        """
        контроль надёжности пароля.
        Анализ производится на основании данных PasswordStats
        """
        password = self.parameters_dict.get("password")

        if password is None:
            logger.warning(T.password_not_set)
            return

        stats = PasswordStats(password=password)

        strength_str, strength_level = self.classify_strength(stats.strength())
        entropy_str, entropy_level = self.classify_entropy(stats.entropy_bits)
        level = max(strength_level, entropy_level)
        self.log_by_password_level(
            level=level, strength_str=strength_str, entropy_str=entropy_str
        )

    @staticmethod
    def log_by_password_level(level, strength_str, entropy_str) -> None:
        """
        Программа выдаёт лог разного уровня исходя из надёжности пароля.

        :param level: Максимальный уровень сообщений о е надёжности пароля.
        :param strength_str: Сообщение strength анализа пароля.
        :param entropy_str: Сообщение entropy анализа пароля.

        :return: None
        """
        # noinspection PyUnreachableCode
        match level:
            case logging.DEBUG:
                logger.debug(f"Пароль {strength_str}, {entropy_str}")
            case logging.INFO:
                logger.info(f"Пароль {strength_str}, {entropy_str}")
            case logging.WARNING:
                logger.warning(f"Пароль {strength_str}, {entropy_str}")
            case logging.ERROR:
                logger.error(f"Пароль {strength_str}, {entropy_str}")
            case _:
                logger.critical("Неизвестная ошибка {strength_str} {entropy_str}")

    @staticmethod
    def classify_strength(x: float) -> tuple[str, int]:
        """
        На основании strength формируются часть сообщения и уровень лога

        :param x: strength

        :return: tuple[Часть сообщения, уровень лога]
        """
        match x:
            case _ if 0.0 <= x < 0.25:
                return "очень слабый", logging.ERROR
            case _ if 0.25 <= x < 0.5:
                return "слабый", logging.WARNING
            case _ if 0.5 <= x < 0.75:
                return "средний", logging.INFO
            case _ if 0.75 <= x:
                return "надёжный", logging.DEBUG
        return "Неизвестная ошибка", logging.CRITICAL

    @staticmethod
    def classify_entropy(x: int) -> tuple[str, int]:
        """
        На основании entropy формируются часть сообщения и уровень лога

        :param x: entropy

        :return: tuple[Часть сообщения, уровень лога]
        """
        match x:
            case _ if 0 <= x < 28:
                return "ненадежный (взламывается мгновенно)", logging.ERROR
            case _ if 28 <= x < 50:
                return " уязвим к перебору", logging.WARNING
            case _ if 0.50 <= x:
                return "высоко-стойкий", logging.DEBUG
        return "Неизвестная ошибка", logging.CRITICAL

    def _run_archive_process(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """
        Запускает процесс архивации.

        :param cmd: Список строк, собрав которые, получаем часть команды для формирования архива

        :return:
        """

        # Определяем кодировку для вывода
        encoding = "cp866" if sys.platform == "win32" else "utf-8"

        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding=encoding,
            errors="replace",
        )

    @staticmethod
    def _mask_password_in_cmd(cmd: list[str], password: str | None) -> list[str]:
        """
        Маскирует пароль в команде для логирования
        :param cmd: cmd для вызова архиватора
        :param password: пароль архива
        :return:
        """
        if not password:
            return cmd

        masked_cmd = cmd.copy()
        for index, item in enumerate(masked_cmd):
            if item.find(password) != -1:
                masked_cmd[index] = f"-p{'*' * len(password)}"

        return masked_cmd

    def get_archiver_program(self) -> str:
        """
        Инициализирует поиск пути к программе архиватору.

        :return: Полный путь к программе архиватору

        Raises:
            OSError: Если программа не найдена в системе
        """
        logger.debug(T.init_FileArchiving)

        # ПФормирование параметров для поиска программы
        config_file_path = self.parameters_dict["config_file_path"]
        standard_program_paths = self.parameters_dict.get(
            "archiver_standard_program_paths"
        )
        programme_full_name = self.parameters_dict["archiver_name"]

        # Поиск пути к программе архиватору
        _search_programme = self.SearchProgramme()
        programme_path = _search_programme.get_path(
            config_file_path=config_file_path,
            standard_program_paths=standard_program_paths,
            programme_full_name=programme_full_name,
        )

        # Проверка наличия архиватора
        if not programme_path:
            logger.critical("")
            raise OSError(T.archiver_not_found)

        return programme_path
