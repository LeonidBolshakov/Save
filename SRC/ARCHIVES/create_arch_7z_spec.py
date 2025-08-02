import subprocess
from pathlib import Path
import sys
import os
import logging

from mypy.checkpattern import self_match_type_names

logger = logging.getLogger(__name__)  # Используем логгер по имени модуля

from SRC.ARCHIVES.archiver import Archiver
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class CreateArch7zSpec(Archiver):
    """
    Класс для работы со специфичным архивом 7z.

    Специфика архива:
    1. Формируется самораспаковывающийся архив (SFX).
    2. Архивируемые файлы передаются через список в файле.
    3. Поддерживает шифрование паролем и защиту имен файлов.

    Attributes:
        seven_zip_exe_path (str): Путь к исполняемому файлу 7z.exe
        work_dir (str): Рабочая директория для выполнения команд
    """

    def __init__(
        self,
        exe_path: str,
        work_dir: str | None = None,
    ):
        """
        Инициализирует экземпляр класса.

        Args:
            exe_path: Абсолютный путь к исполняемому файлу 7z.exe
            work_dir: Рабочая директория для выполнения команд архивации
                     (по умолчанию текущая директория)

        Raises:
            ValueError: Если не указан путь к архиву
            FileExistsError: Если по указанному пути архива уже существует файл/директория с именем архива
            ValueError: Если архив имеет неверное расширение (не .exe)
            FileNotFoundError: Если файл со списком архивируемых файлов не существует
        """
        super().__init__(exe_path, work_dir)

        logger.debug(T.init_arch)

        self.seven_zip_exe_path = exe_path  # Сохраняем путь на программу 7z
        self.work_dir = work_dir or os.getcwd()  # Текущая директория по умолчанию

    def create_archive(
        self,
        archive_path: str,
        list_file: str,
        password: str | None = None,
        compression_level: int = 5,
    ) -> int:
        """
        Выполняет создание архива.

        Process:
        1. Формирует команду архивации
        2. Выполняет команду через subprocess
        3. Обрабатывает результаты выполнения

        Parameters:
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
        self._check_all_params(
            archive_path=archive_path,
            list_file=list_file,
            compression_level=compression_level,
        )

        # Определяем кодировку для вывода
        encoding = "cp866" if sys.platform == "win32" else "utf-8"

        # Запускаем программу 7z
        cmd = self._get_cmd_archiver(
            archive_path,
            password=password,
            compression_level=compression_level,
            list_file=list_file,
        )
        logger.debug(
            T.starting_archiving.format(
                cmd=self._mask_password_in_cmd(cmd=cmd, password=password)
            )
        )
        try:
            process = self._run_archive_process(cmd=cmd, encoding=encoding)
            return process.returncode
        except Exception as e:
            logger.critical({e})
            raise RuntimeError(T.error_starting_archiving.format(e=e))

    def _check_all_params(
        self, archive_path: Path | str | None, list_file: str, compression_level: int
    ) -> None:
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
        self._check_arch(archive_path=archive_path, compression_level=compression_level)
        self._check_list_file(list_file=list_file)

    def _check_arch(
        self, archive_path: Path | str | None, compression_level: int
    ) -> None:
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

        if archive_path is None:
            raise ValueError(T.no_path_local)
        archive = Path(archive_path)

        self._check_arch_exists(archive_path=archive)
        self._check_arch_ext(archive_path=archive)
        self._check_validate_of_compression(compression_level=compression_level)

    @staticmethod
    def _check_arch_exists(archive_path: Path):
        """
        Проверяет отсутствие файла/директории с заданным именем.

        Args:
            archive_path: Путь к архиву для проверки

        Raises:
            FileExistsError: Если по указанному пути уже существует файл или директория
        """
        if not archive_path.exists():
            return

        obj_type = "файл" if archive_path.is_file() else "директория"
        raise FileExistsError(
            T.arch_exists.format(obj_type=obj_type, arch_path=str(archive_path))
        )

    @staticmethod
    def _check_arch_ext(archive_path: Path):
        """
        Проверяет расширение файла архива.

        Args:
            archive_path: Путь к архиву для проверки

        Raises:
            ValueError: Если расширение архива не .exe
        """
        if archive_path.suffix != C.ARCHIVE_SUFFIX:
            logger.critical("")
            raise ValueError(
                T.invalid_file_extension.format(
                    suffix=archive_path.suffix, archive_suffix=C.ARCHIVE_SUFFIX
                )
            )

    @staticmethod
    def _check_list_file(list_file: str) -> None:
        """
        Проверяет существование файла со списком архивируемых файлов

        :parameter:
            list_file - Путь на файл, содержащий список архивируемых файлов

        Raises:
            FileNotFoundError: Если файл со списком не существует
        """
        # Проверяем существует ли список архивируемых файлов
        list_file_path = Path(list_file)
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

    def _run_archive_process(
        self, cmd: list[str], encoding: str
    ) -> subprocess.CompletedProcess:
        """Запускает процесс архивации."""
        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding=encoding,
            errors="replace",
            cwd=self.work_dir,
        )

    def _get_cmd_archiver(
        self,
        archive_path: str,
        password: str | None,
        compression_level: int,
        list_file: str,
    ) -> list[str]:
        """
        Формирует команду для выполнения архивации с помощью 7z.

        Returns:
            list[str]: Список аргументов команды для subprocess.run

        Note:
            Пароль в логах маскируется звездочками для безопасности
        """
        cmd = [
            self.seven_zip_exe_path,  # Путь к программе архиватору
            "a",  # Добавляем файлы в архив
            *(
                [f"-p{password}"] if password else []
            ),  # Если пароль не задан параметр не формируется
            "-mhe=on",  # Если задан пароль шифровать имена файлов
            "-sfx",  # Создавать самораспаковывающийся файл
            f"-mx={compression_level}",  # Уровень компрессии
            archive_path,  # Полный путь на формируемый архив
            f"@{list_file}",
            # Добавляем параметры для подавления вывода
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
