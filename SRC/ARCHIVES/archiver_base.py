import subprocess
from pathlib import Path
import sys
import logging

logger = logging.getLogger(__name__)  # Используем логгер по имени модуля

from SRC.GENERAL.textmessage import TextMessage as T


class CreateArch7zSpec:
    """
    Класс для работы со специфичным архивом 7z.

    Специфика архива:
    1. Формируется самораспаковывающийся архив (SFX).
    2. Архивируемые файлы передаются через список в файле.
    3. Поддерживает шифрование паролем и защиту имен файлов.
    """

    def __init__(
        self,
        archiver_path: str,
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

        self.archiver_path = archiver_path
        self.parameters_dict = parameters_dict

    def create_archive(self) -> int:
        """
        Выполняет создание архива.

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
            compression_level: int = 5. Уровень компрессии в диапазоне [0,9]
            0 - нет компрессии, 9 - ультра компрессия

        Returns:
            int: 0 если архивация успешна, 1 не фатальные ошибки, 2 - фатальные ошибки

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

        # Выгрузка параметров
        archive_path: str = str(
            Path(
                self.parameters_dict["archive_catalog"],
                self.parameters_dict["local_archive_name"],
            )
        )
        self.parameters_dict["archive_path"] = archive_path
        list_archive_file_paths: str = self.parameters_dict["list_archive_file_paths"]
        password: str = self.parameters_dict["password"]
        compression_level: int = self.parameters_dict.get("compression_level", 5)
        self.parameters_dict["compression_level"] = compression_level

        # Контроль параметров
        self._check_all_params(self.parameters_dict)

        # Определяем кодировку для вывода
        encoding = "cp866" if sys.platform == "win32" else "utf-8"

        # Запускаем программу 7z
        cmd = self._get_cmd_archiver()
        logger.debug(
            T.starting_archiving.format(
                cmd=self._mask_password_in_cmd(cmd=cmd, password=password)
            )
        )
        try:
            process = self._run_archive_process(cmd=cmd, encoding=encoding)
            if process.returncode == 1:
                logger.warning(process.stderr)
            if process.returncode > 1:
                logger.error(process.stderr)
            return process.returncode
        except Exception as e:
            logger.critical("")
            raise RuntimeError(T.error_starting_archiving.format(e=e))

    def _check_all_params(self, parameters_dict: dict) -> None:
        """
        Выполняет комплексную проверку всех переданных параметров.

        Выполняет следующие проверки:
        1. Корректность пути и имени архива
        2. Наличие и корректность файла со списком файлов

        :Parameters: archive_path - Путь на архив.
        :Parameters: list_file - Путь на файл, содержащий список архивируемых файлов.
            Структура файла списка архивируемых файлов описана.
        :Parameters: compression_level - Уровень компрессии (сжатия) от 0 до 9 включительно

        Raises:
            Различные исключения в зависимости от типа ошибки
        """
        self._check_arch(parameters_dict)
        self._check_list_file(parameters_dict)

    def _check_arch(self, parameters_dict: dict) -> None:
        """
        Проверяет корректность параметров архивации.

        Выполняет:
        1. Проверку наличия пути к архиву
        2. Проверку отсутствия файла/директории архива.
            Архив не должен изменять существующие данные
        3. Проверку расширения архива (.exe)
        4. Проверку уровня сжатия - целое число в диапазоне [0-9]

        :Parameters: archive_path - Путь на архив.
        :Parameters:compression_level -Уровень компрессии (сжатия)

        Raises:
            ValueError: Если не указан путь или неверное расширение,
            или невалидный уровень сжатия
            FileExistsError: Если по пути архива уже существует объект
        """
        # Извлекаем параметры
        archive_path: str = parameters_dict["archive_path"]
        compression_level: int = parameters_dict["compression_level"]

        # Контроль параметров
        if archive_path is None:
            raise ValueError(T.no_path_local)

        self._check_arch_exists(archive_path=archive_path)
        self._check_validate_of_compression(compression_level=compression_level)

    @staticmethod
    def _check_arch_exists(archive_path: str):
        """
        Проверяет отсутствие файла/директории с заданным именем.

        Args:
            archive_path: Путь к архиву для проверки

        Raises:
            FileExistsError: Если по указанному пути уже существует файл или директория
        """
        if not Path(archive_path).exists():
            return

        obj_type = "файл" if Path(archive_path).is_file() else "директория"
        raise FileExistsError(
            T.arch_exists.format(obj_type=obj_type, arch_path=archive_path)
        )

    @staticmethod
    def _check_list_file(parameters_list: dict) -> None:
        """
        Проверяет существование файла со списком архивируемых файлов

        :parameter:
            list_file - Путь на файл, содержащий список архивируемых файлов

        Raises:
            FileNotFoundError: Если файл со списком не существует
        """
        # Проверяем существует ли список архивируемых файлов
        list_archive_file_paths = parameters_list["list_archive_file_paths"]
        list_file_path = Path(list_archive_file_paths)
        if not list_file_path.exists():
            logger.critical("")
            raise FileNotFoundError(
                T.not_found_list_file_path.format(list_file_path=list_file_path)
            )
        logger.debug(T.exists_list_file.format(list_file_path=list_file_path))

    @staticmethod
    def _check_validate_of_compression(compression_level: int) -> None:
        """
        Проверка параметра "Уровень компрессии". Параметр должен быть целым число в сегменте [0,9]
        :param compression_level: (int) - Уровень компрессии
        :return: None
        """
        if not isinstance(compression_level, int):
            raise ValueError(
                T.error_in_compression_level.format(level=compression_level)
            )

        if 0 <= compression_level <= 9:
            return

        raise ValueError(T.error_in_compression_level)

    @staticmethod
    def _run_archive_process(
        cmd: list[str], encoding: str
    ) -> subprocess.CompletedProcess:
        """Запускает процесс архивации."""
        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding=encoding,
            errors="replace",
        )

    def _get_cmd_archiver(self) -> list[str]:
        """
        Формирует команду для выполнения архивации с помощью 7z.

        Parameters:
            self

        Used parameters_dict keys:
            archive_path: str - Полный путь создаваемого архива
            list_archive_file_paths: str - Полный путь на файл, содержащий имена архивируемых файлов
            password: str | None = None - Пароль. Если пароль на задан файл не архивируется
            compression_level: int = 5. Уровень компрессии в диапазоне [0,9]
            0 - нет компрессии, 9 - ультра компрессия
            archive_extension: str - Расширение архива

        Returns:
            list[str]: Список аргументов команды для subprocess.run

        Note:
            Пароль в логах маскируется звездочками для безопасности
        """
        archive_path: str = self.parameters_dict["archive_path"]
        password: str = self.parameters_dict["password"]
        compression_level: int = self.parameters_dict["compression_level"]
        list_archive_file_paths: str = self.parameters_dict["list_archive_file_paths"]
        archive_extension: str = self.parameters_dict["archive_extension"]
        cmd = [
            self.archiver_path,  # Путь к программе архиватору
            "a",  # Добавляем файлы в архив
            *(
                [f"-p{password}"] if password else []
            ),  # Если пароль не задан параметр не формируется
            "-mhe=on",  # Если задан пароль шифровать имена файлов
            *(
                ["-sfx"] if archive_extension == ".exe" else []
            ),  # Если расширение не exe - параметр не формируется
            f"-mx={compression_level}",  # Уровень компрессии
            archive_path,  # Полный путь на формируемый архив
            f"@{list_archive_file_paths}",
            # Добавляем параметры для подавления лишнего вывода
            "-bso0",  # отключить вывод в stdout
            "-bsp0",  # отключить индикатор прогресса
        ]

        return cmd

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
        masked_cmd[2] = f"-p{'*' * len(password)}"
        return masked_cmd
