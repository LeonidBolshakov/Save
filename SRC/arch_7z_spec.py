import subprocess
from pathlib import Path
import sys
import os
import logging

logger = logging.getLogger(__name__)  # Используем логгер по имени модуля


class Arch7zSpec:
    """
    Класс для работы со специфичным архивом 7z.

    Специфика архива:
    1. Формируется самораспаковывающийся архив (SFX).
    2. Архивируемые файлы передаются через список в файле.
    3. Поддерживает шифрование паролем и защиту имен файлов.

    Attributes:
        password (str): Пароль для архива (необязательный)
        arch_path (str): Путь к создаваемому архиву
        list_file (str): Путь к файлу со списком файлов для архивации
        seven_zip_path (str): Путь к исполняемому файлу 7z.exe
        work_dir (str): Рабочая директория для выполнения команд
    """

    def __init__(
        self,
        arch_path: str,
        list_file: str,
        seven_zip_path: str,
        password: str = "",
        work_dir: str | None = None,
    ):
        """
        Инициализирует экземпляр класса для создания SFX-архива.

        Args:
            arch_path: Путь к создаваемому SFX-архиву (должен иметь расширение .exe)
            list_file: Путь к файлу, содержащему список файлов для архивации
            seven_zip_path: Абсолютный путь к исполняемому файлу 7z.exe
            password: Пароль для шифрования архива (по умолчанию пустая строка)
            work_dir: Рабочая директория для выполнения команд архивации
                     (по умолчанию текущая директория)

        Raises:
            ValueError: Если не указан путь к архиву
            FileExistsError: Если по указанному пути архива уже существует файл/директория
            ValueError: Если архив имеет неверное расширение (не .exe)
            FileNotFoundError: Если файл со списком архивируемых файлов не существует
        """
        logger.debug("Инициализация Arch7zSpec")

        self.password = password
        self.arch_path = arch_path
        self.list_file = list_file
        self.seven_zip_path = seven_zip_path  # Сохраняем путь на программу 7z
        self.work_dir = work_dir or os.getcwd()  # Текущая директория по умолчанию

        self.check_all_params()

    def check_all_params(self):
        """
        Выполняет комплексную проверку всех параметров объекта.

        Выполняет следующие проверки:
        1. Корректность пути и имени архива
        2. Наличие и корректность файла со списком файлов

        Raises:
            Различные исключения в зависимости от типа ошибки
        """
        self.check_arch()
        self.check_list_file()

    def check_arch(self):
        """
        Проверяет корректность параметров архива.

        Выполняет:
        1. Проверку наличия пути к архиву
        2. Проверку отсутствия файла/директории по пути архива
        3. Проверку расширения архива (.exe)

        Raises:
            ValueError: Если не указан путь или неверное расширение
            FileExistsError: Если по пути архива уже существует объект
        """
        arch_path = self.check_arch_path()
        self.check_arch_exists(arch_path)
        self.check_arch_ext(arch_path)

    def check_arch_path(self) -> Path:
        """
        Проверяет наличие пути к архиву, в которос собираются сохраняемые файлы.

        Returns:
            Path: Объект Path для пути к архиву

        Raises:
            ValueError: Если путь к архиву не указан
        """
        if self.arch_path:
            return Path(self.arch_path)
        else:
            message = "Не задан путь на архив, в который собираются сохраняемые файлы"
            logger.error(message)
            raise ValueError(message)

    @staticmethod
    def check_arch_exists(arch_path: Path):
        """
        Проверяет отсутствие файла/директории по пути архива.

        Args:
            arch_path: Путь к архиву для проверки

        Raises:
            FileExistsError: Если по указанному пути уже существует файл или директория
        """
        if arch_path.exists():
            if arch_path.is_file():
                message = f"существует файл {arch_path}, имя которого, совпадает с именем архива. Архивация невозможна."
                logger.error(message)
                raise FileExistsError(message)
            else:
                message = f"существует директория {arch_path}, имя которой, совпадает с именем архива. Архивация невозможна."
                logger.error(message)
                raise FileExistsError(message)

    @staticmethod
    def check_arch_ext(arch_path: Path):
        """
        Проверяет расширение файла архива.

        Args:
            arch_path: Путь к архиву для проверки

        Raises:
            ValueError: Если расширение архива не .exe
        """
        if arch_path.suffix != ".exe":
            message = f"Недопустимое расширение файла архива: {arch_path.suffix} - должно быть exe"
            logger.critical(message)
            raise ValueError(message)

    def check_list_file(self):
        """
        Проверяет существование файла со списком архивируемых файлов.

        Raises:
            FileNotFoundError: Если файл со списком не существует
        """
        # Проверяем существует ли список архивируемых файлов
        list_file_path = Path(self.list_file)
        message = f"Не найден файл списка для архивации: {list_file_path}"
        if not list_file_path.exists():
            logger.critical(message)
            raise FileNotFoundError(message)
        logger.debug(f"Файл списка файлов архивации существует: {list_file_path}")

    def make_archive(self) -> bool:
        """
        Выполняет создание самораспаковывающегося архива.

        Process:
        1. Формирует команду архивации
        2. Выполняет команду через subprocess
        3. Обрабатывает результаты выполнения

        Returns:
            bool: True если архивация успешна, False если произошла ошибка

        Note:
            Для Windows используется кодировка cp866 для корректного отображения вывода
        """
        # Определяем кодировку для вывода
        encoding = "cp866" if sys.platform == "win32" else "utf-8"

        # Запускаем программу 7z
        cmd = self.get_cmd_archiver()
        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors="replace",  # Автозамена нечитаемых символов
                cwd=self.work_dir,  # Указываем рабочую директорию
            )
        except Exception as e:
            logger.critical(
                f"Ошибка при запуске процесса архивации: {e}"
            )  # Оригинальный вывод
            return False
        else:
            if process.returncode != 0:
                # Выводим ошибки в LOG
                logger.error(f"stderr: {process.stderr}")
                logger.error("Архивация завершена с ошибками")
                return False
            else:
                logger.info("Архивация завершена успешно")
                return True

    def get_cmd_archiver(self) -> list[str]:
        """
        Формирует команду для выполнения архивации с помощью 7z.

        Returns:
            list[str]: Список аргументов команды для subprocess.run

        Note:
            Пароль в логах маскируется звездочками для безопасности
        """
        cmd = [
            self.seven_zip_path,
            "a",  # Добавляем файлы в архив
            *(
                [f"-p{self.password}"] if self.password else []
            ),  # Если пароль не задан параметр не формируется
            "-mhe=on",  # Если задан пароль шифровать имена файлов
            "-sfx",  # Создавать самораспаковывающийся файл
            self.arch_path,
            f"@{self.list_file}",
            # Добавляем параметры для подавления вывода
            "-bso0",  # отключить вывод в stdout
            "-bsp0",  # отключить индикатор прогресса
        ]

        # Создаем безопасную копию команды для логирования
        cmd_print = cmd.copy()
        if self.password:
            # Маскируем пароль в логах
            cmd_print[2] = f"-p{'*' * len(self.password)}"
        logger.info("Запуск архивации: %s", cmd_print)

        return cmd
