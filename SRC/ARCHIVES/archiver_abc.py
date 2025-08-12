from abc import ABC, abstractmethod
import subprocess
from typing import Any
from pathlib import Path
from typing import Protocol, Callable
import sys
import logging

logger = logging.getLogger(__name__)  # Используем логгер по имени модуля

from password_strength import PasswordStats

from SRC.GENERAL.checkparameter import get_parameter
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class BackupManagerArchiver(Protocol):
    create_archive: Callable[[dict[str, Any]], str | None]


class Archiver(ABC, BackupManagerArchiver):
    """
    Архиватор - Класс для создания архивов.

    Специфика архива:
    1. Есть файл с путями архивируемых файлов.
    2. Поддерживает шифрование паролем и защиту имен файлов.

    Использует следующие parameters_dict ключи (включая базовый класс) :
        Archiver: - Дочерний класс архиватора. Например, Archiver7z
        SearchProgramme: - Дочерний класс для поиска программы. Например, SearchProgramme7Z
        archive_extension: str - Расширение архива. Например, '.exe'
        archiver_name: str - Шаблон имени программы
        archiver_standard_program_paths: list[str] - Стандартные пути программы (Опционально)
        config_file_path: str - Путь на файл конфигурации с путями программ
        list_archive_file_paths: str - Путь на файл, содержащий архивируемые файлы
        local_archive_name: str - Имя локального архива
        password: str - Пароль (опционально)

    Raises:
        ValueError: Если не указан путь к архиву
        FileExistsError: Если по указанному пути архива уже существует файл/директория с именем архива
        ValueError: Если архив имеет неверное расширение (не .exe)
        FileNotFoundError: Если файл со списком архивируемых файлов не существует
    """

    def create_archive(
        self,
        parameters_dict: dict[str, Any],
    ) -> str | None:
        """
        Выполняет создание архива.
        Этот метод использует BackupManager(ABC)

        Process:
        1. Формирует команду архивации
        2. Выполняет команду через subprocess
        3. Обрабатывает результаты выполнения

        Parameters:
            parameters_dict: dict[str, Any] - Словарь параметров

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

        search_programme = get_parameter(
            parameter=C.PAR___SEARCH_PROGRAMME, parameters_dict=parameters_dict
        )

        # Загрузка параметров
        archive_path = self.get_archive_path(parameters_dict)

        try:
            parameters_dict[C.PAR_ARCHIVE_PATH] = archive_path
        except KeyError as e:
            logger.critical(T.error_parameter_archiver.format(param=C.PAR_ARCHIVE_PATH))
            raise KeyError from e

        list_archive_file_paths = get_parameter(
            C.PAR_LIST_ARCHIVE_FILE_PATHS, parameters_dict=parameters_dict
        )

        password: str | None = parameters_dict.get(C.PAR_PASSWORD)

        # Контроль параметров
        self._check_all_params(parameters_dict)

        # готовим командную строку для запуска архиватора
        archiver_program = self.get_archiver_program(parameters_dict)
        cmd = self.get_cmd_archiver(archiver_program, parameters_dict)
        logger.debug(
            T.starting_archiving.format(
                cmd=self._mask_password_in_cmd(cmd=cmd, password=password)
            )
        )

        # Запускаем программу архиватор
        return (  # archive_path было задано как имя архива при формировании cmd
            archive_path
            if self._run_archiver(cmd=cmd, archive_path=archive_path, password=password)
            else None
        )

    def _run_archiver(self, cmd: list[str], archive_path: str, password: str) -> bool:
        """
        запуск программы архиватора по заранее сформированной разобранной строке

        :param cmd: Список строк, соединив которые, получаем команду для запуска программы архиватора.
        :param archive_path: Путь на архив
        :param password: Пароль

        :return: True, если сформирован "хороший" архив, False в противном случае

        :raise: RuntimeError - была критическая ошибка при архивировании
        """
        try:
            process = self._run_archive_process(cmd=cmd)
            if process.returncode == 1:
                logger.warning(self._error_subprocess(process, cmd, password))
            if process.returncode > 1:
                logger.error(self._error_subprocess(process, cmd, password))
                return False
            return True
        except Exception as e:
            logger.critical(
                ""
            )  # Для поднятия уровня логов до CRITICAL. В LOG не выводится обработчиками
            raise RuntimeError(T.error_starting_archiving.format(e=e))

    def _error_subprocess(self, process, cmd: list[str], password: str):
        return logger.error(
            T.error_subprocess.format(
                cmd_mask=self._mask_password_in_cmd(cmd=cmd, password=password),
                stderr=process.stderr,
            )
        )

    @staticmethod
    def get_archive_path(parameters_dict: dict[str:Any]) -> str:
        """
        Формирует и возвращает полный путь на архив

        :return: (str) полный путь на архив
        """

        archive_dir = parameters_dict[C.PAR_ARCHIVE_DIR]
        archive_name = get_parameter(
            C.PAR_LOCAL_ARCHIVE_NAME, parameters_dict=parameters_dict
        )
        return str(Path(archive_dir, archive_name))

    @abstractmethod  # формирует команду для выполнения subprocess.run
    def get_cmd_archiver(
        self, archiver_program: str, parameters_dict: dict[str, Any]
    ) -> list[str]:
        pass

    def _check_all_params(self, parameters_dict: dict[str, Any]) -> None:
        """
        Выполняет комплексную проверку всех переданных параметров.

        Выполняет следующие проверки:
        1. Корректность пути и имени архива
        2. Наличие и корректность файла со списком файлов

        :Parameters: parameters_dict: dict[str, Any] Словарь параметров.

        Raises:
            Различные исключения в зависимости от типа ошибки
        """
        self._check_arch_exists(parameters_dict)
        self._check_list_file(parameters_dict)
        self._check_password(parameters_dict)

    @staticmethod
    def _check_arch_exists(parameters_dict: dict[str, Any]) -> None:
        """
        Проверяет отсутствие файла/директории с заданным именем.

        Args:
            parameters_dict: dict[str, Any] Словарь параметров.

        Raises:
            FileExistsError: Если по указанному пути уже существует файл или директория
        """
        archive_path: str = parameters_dict[C.PAR_ARCHIVE_PATH]
        if not Path(archive_path).exists():
            return

        obj_type = "файл" if Path(archive_path).is_file() else "директория"
        raise FileExistsError(
            T.arch_exists.format(obj_type=obj_type, arch_path=archive_path)
        )

    @staticmethod
    def _check_list_file(parameters_dict: dict[str, Any]) -> None:
        """
        Проверяет существование файла со списком архивируемых файлов

        :parameter:
            parameters_dict: dict[str, Any] Словарь параметров.

        Raises:
            FileNotFoundError: Если файл со списком не существует
        """
        # Проверяем существует ли список архивируемых файлов
        list_archive_file_paths = get_parameter(
            C.PAR_LIST_ARCHIVE_FILE_PATHS, parameters_dict=parameters_dict
        )
        list_file_path = Path(list_archive_file_paths)
        if not list_file_path.exists():
            logger.critical(
                ""
            )  # Для поднятия уровня логов до CRITICAL. В LOG не выводится обработчиками
            raise FileNotFoundError(
                T.not_found_list_file_path.format(
                    list_file_path=list_file_path,
                    env=Path(C.VARIABLES_DOTENV_PATH).absolute(),
                    parameter=C.ENV_LIST_PATH_TO_LIST_OF_ARCHIVABLE_FILES,
                    default=C.LIST_PATH_TO_LIST_OF_ARCHIVABLE_FILES_DEF,
                )
            )
        logger.debug(T.exists_list_file.format(list_file_path=list_file_path))

    def _check_password(self, parameters_dict: dict[str, Any]) -> None:
        """
        контроль надёжности пароля.
        Анализ производится на основании данных PasswordStats
        """
        password = parameters_dict.get(C.PAR_PASSWORD)

        if password is None:
            logger.info(T.password_not_set)
            return

        stats = PasswordStats(password=password)

        strength_str, strength_level = self.classify_strength(stats.strength())
        entropy_str, entropy_level = self.classify_entropy(stats.entropy_bits)
        level = max(strength_level, entropy_level)
        self.log_by_password_level(
            level=level, strength_str=strength_str, entropy_str=entropy_str
        )

    def log_by_password_level(self, level, strength_str, entropy_str) -> None:
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
                logger.debug(self.message_about_password(strength_str, entropy_str))
            case logging.INFO:
                logger.info(self.message_about_password(strength_str, entropy_str))
            case logging.WARNING:
                logger.warning(self.message_about_password(strength_str, entropy_str))
            case logging.ERROR:
                logger.error(self.message_about_password(strength_str, entropy_str))
            case _:
                logger.critical(T.unintended_log_level.format(level=level))

    @staticmethod
    def message_about_password(strength_str: str, entropy_str: str) -> str:
        return T.password_message.format(
            strength_str=strength_str,
            entropy_str=entropy_str,
            program=C.PROGRAM_WRITE_VARS,
            parameter=C.ENV_PASSWORD_ARCHIVE,
        )

    @staticmethod
    def classify_strength(x: float) -> tuple[str, int]:
        """
        На основании strength формируются часть сообщения и уровень лога

        :param x: strength

        :return: tuple[Часть сообщения, уровень лога]
        """
        match x:
            case _ if 0.0 <= x < 0.25:
                return T.strength_very_weak, logging.WARNING
            case _ if 0.25 <= x < 0.5:
                return T.strength_weak, logging.INFO
            case _ if 0.5 <= x < 0.75:
                return T.strength_medium, logging.DEBUG

        return T.strength_strong, logging.DEBUG

    @staticmethod
    def classify_entropy(x: int) -> tuple[str, int]:
        """
        На основании entropy формируются часть сообщения и уровень лога

        :param x: entropy

        :return: tuple[Часть сообщения, уровень лога]
        """
        match x:
            case _ if 0 <= x < 28:
                return T.entropy_Unreliable, logging.WARNING
            case _ if 28 <= x < 50:
                return T.entropy_brute_force, logging.INFO
            case _ if 0.50 <= x:
                return T.entropy_highly, logging.DEBUG
        return T.error_unknown, logging.CRITICAL

    @staticmethod
    def _run_archive_process(cmd: list[str]) -> subprocess.CompletedProcess:
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
            text=True,
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
                masked_cmd[index] = masked_cmd[index].replace(
                    password, f"{'*' * len(password)}"
                )

        return masked_cmd

    @staticmethod
    def get_archiver_program(parameters_dict: dict[str, Any]) -> str:
        """
        Инициализирует поиск пути к программе архиватору.

        :return: Полный путь к программе архиватору

        Raises:
            OSError: Если программа не найдена в системе
        """
        logger.debug(T.init_SearchProgramme)

        # Формирование параметров для поиска программы
        config_file_path = get_parameter(
            C.PAR_CONFIG_FILE_PATH, parameters_dict=parameters_dict, level=logging.DEBUG
        )
        if config_file_path is None:
            config_file_path = C.CONFIG_FILE_WITH_PROGRAM_NAME_DEF

        standard_program_paths = get_parameter(
            C.PAR_STANDARD_PROGRAM_PATHS,
            parameters_dict=parameters_dict,
            level=logging.DEBUG,
        )
        programme_full_name = get_parameter(
            C.PAR_ARCHIVER_NAME, parameters_dict=parameters_dict
        )

        # Создание объекта класса поиска программы
        SearchProgramme = get_parameter(
            C.PAR___SEARCH_PROGRAMME, parameters_dict=parameters_dict
        )

        _search_programme = SearchProgramme()

        # Поиск пути к программе архиватору
        programme_path = _search_programme.get_path(
            config_file_path=config_file_path,
            standard_program_paths=standard_program_paths,
            programme_full_name=programme_full_name,
        )

        # Проверка наличия архиватора
        if not programme_path:
            logger.critical(
                ""
            )  # Для поднятия уровня логов до CRITICAL. В LOG не выводится обработчиками
            raise OSError(T.archiver_not_found)

        return programme_path
