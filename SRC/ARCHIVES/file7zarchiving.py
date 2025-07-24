from pathlib import Path
import logging

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)

# Импорт зависимостей
from SRC.ARCHIVES.seven_z_manager import SevenZManager
from SRC.ARCHIVES.arch_7z_spec import Arch7zSpec
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constant import Constant as C
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
        list_archive_file: str = C.LIST_ARCHIVE_FILE,
        config_file: str = C.DEFAULT_CONFIG_FILE,
        archive_name: str = C.DEFAULT_LOCAL_ARCHIVE_FILE,
    ):
        """Инициализация архиватора.

        Args:
            list_archive_file: Путь к файлу со списком файлов для архивации
            config_file: Путь к файлу конфигурации
            archive_name: Имя создаваемого архива
        """
        self.list_archive_file = list_archive_file
        self.config_file = config_file
        self.archive_name = archive_name
        self._init_7z(config_file=config_file)  # Инициализация 7z

    def _init_7z(self, config_file):
        """Инициализирует путь к 7z.exe через менеджер конфигурации.

        Raises:
            OSError: Если 7z.exe не найден на системе
        """
        logger.debug(T.init_FileArchiving)

        # Получение пути к 7z.exe из конфигурации
        seven_z_manager = SevenZManager(config_file)
        self.seven_z_exe_path = seven_z_manager.get_7z_path()

        # Проверка наличия 7z.exe
        if not self.seven_z_exe_path:
            logger.critical("")
            raise OSError(T.not_found_7z)

    def make_local_archive(self, temp_dir: str) -> str:
        """Создает 7z-архив в указанной временной директории.

        Args:
            temp_dir: Путь к временной директории для архива

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
            local_path = Path(temp_dir, self.archive_name)
            local_path_str = str(local_path)
            logger.debug(T.path_local_archive.format(local_path_str=local_path_str))

            # Создание спецификации архива
            arch_7z_spec = Arch7zSpec(
                arch_path=local_path_str,
                list_file=self.list_archive_file,
                seven_zip_exe_path=self.seven_z_exe_path,
                password=variables.get_var(
                    C.ENV_PASSWORD_ARCHIVE
                ),  # Безопасное получение пароля
            )

            # Создание архива
            arch_7z_spec.make_archive()
            return local_path_str

        except Exception as e:
            raise
