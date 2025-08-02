from pathlib import Path
import logging

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)

# Импорт зависимостей
from SRC.ARCHIVES.search_7z_exe import Search7zExe
from SRC.ARCHIVES.create_arch_7z_spec import CreateArch7zSpec
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.textmessage import TextMessage as T


class File7ZArchiving:
    """Класс для создания 7z-архивов с использованием 7z.exe.

    Обеспечивает:
    - Проверку наличия 7z.exe на системе
    - Создание архивов по заданным параметрам
    - Обработку ошибок архивации
    """

    def __init__(
        self,
        list_archive_file_path: str,
        config_file_path: str,
        local_archive_name: str,
    ):
        """Инициализация архиватора.

        Args:
            list_archive_file_path: Путь к файлу со списком файлов для архивации
            config_file_path: Путь к файлу конфигурации
            local_archive_name: Имя создаваемого архива
        """
        self.list_archive_file = list_archive_file_path
        self.config_file_path = config_file_path
        self.local_archive_name = local_archive_name
        self._init_7z(config_file_path=config_file_path)  # Инициализация пути к 7z.exe

    def _init_7z(self, config_file_path):
        """Инициализирует путь к 7z.exe через менеджер конфигурации.

        Raises:
            OSError: Если 7z.exe не найден на системе
        """
        logger.debug(T.init_FileArchiving)

        # Получение пути к 7z.exe из конфигурации
        self.seven_z_exe_path = Search7zExe(
            config_file_path=config_file_path
        ).get_path()

        # Проверка наличия 7z.exe
        if not self.seven_z_exe_path:
            logger.critical("")
            raise OSError(T.not_found_7z)

    def make_local_archive(
        self,
        temp_dir: str,
        password: str,
        compression_level: int,
    ) -> str:
        """Создает 7z-архив в указанной временной директории.

        Args:
            temp_dir: Путь к временной директории для архива
            password: (str) Пароль
            compression_level: (int) Уровень сжатия

        Returns:
            str: Абсолютный путь к созданному архиву

        Raises:
            RuntimeError: Если произошла ошибка при создании архива
        """
        logger.debug(T.start_create_archive)
        try:
            # Доступ к переменным окружения
            variables = EnvironmentVariables()
            # Формирование пути к архиву
            local_path = Path(temp_dir, self.local_archive_name)
            local_path_str = str(local_path)
            logger.debug(T.path_local_archive.format(local_path_str=local_path_str))

            # Создание архива
            arch_7z_spec = self.get_arch_7z_spec(
                password, compression_level, local_path_str
            )
            arch_7z_spec.create_archive(
                archive_path=local_path_str,
                list_file=self.list_archive_file,
                password=password,
                compression_level=compression_level,
            )
            return local_path_str

        except Exception as e:
            raise Exception(e)

    def get_arch_7z_spec(
        self, password: str, compression_level: int, local_path_str: str
    ):
        """
        Строительство объекта для создания архива
        :param password: (str) Пароль
        :param compression_level: (int). Уровень компрессии
        :param local_path_str: (str) Путь на создаваемый архив
        :return:
        """
        return CreateArch7zSpec(
            exe_path=self.seven_z_exe_path,
        )
