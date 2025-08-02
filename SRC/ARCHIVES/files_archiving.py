from pathlib import Path
import logging

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)

# Импорт зависимостей
from SRC.ARCHIVES.search_programme import SearchProgramme
from SRC.ARCHIVES.create_arch_7z_spec import CreateArch7zSpec
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.textmessage import TextMessage as T


class FilesArchiving:
    """Класс для создания архивов.

    Обеспечивает:
    - Проверку наличия архиватора в системе
    - Создание архивов по заданным параметрам
    - Обработку ошибок архивации
    """

    def __init__(
        self,
        list_archive_file_paths: str,
        archiver_name_template: str,
        config_file_path: str,
        local_archive_name: str,
    ):
        """Инициализация архивации.

        Args:
            list_archive_file_paths: Путь к файлу со списком файлов для архивации
            config_file_path: Путь к файлу конфигурации, возможно содержащий, полный путь к архиватору
            local_archive_name: Имя создаваемого архива
        """
        self.list_archive_file_paths = list_archive_file_paths
        self.archiver_name_template = archiver_name_template
        self.config_file_path = config_file_path
        self.local_archive_name = local_archive_name
        self._init_search(config_file_path=config_file_path)

    def _init_search(self, config_file_path):
        """Инициализирует поиск пути к архиватору.

        Raises:
            OSError: Если программа не найдена в системе
        """
        logger.debug(T.init_FileArchiving)

        # Получение пути к программе
        self.programme_path = SearchProgramme(
            config_file_path=config_file_path
        ).get_path(
            default_programme_paths=self.list_archive_file_paths,
            program_template=self.archiver_name_template,
        )

        # Проверка наличия архиватора
        if not self.programme_path:
            logger.critical("")
            raise OSError(T.archiver_not_found)

    def make_local_archive(
        self,
        dir_archive: str,
        password: str,
        compression_level: int,
    ) -> str:
        """Создает 7z-архив в указанной временной директории.

        Args:
            dir_archive: Путь к директории для архива
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
            local_path = Path(dir_archive, self.local_archive_name)
            local_path_str = str(local_path)
            logger.debug(T.path_local_archive.format(local_path_str=local_path_str))

            # Создание архива
            arch_7z_spec = self.get_arch_7z_spec(
                password, compression_level, local_path_str
            )
            return_code = arch_7z_spec.create_archive(
                archive_path=local_path_str,
                list_file=self.list_archive_file_paths,
                password=password,
                compression_level=compression_level,
            )

            self._handle_process_result(return_code)
            return local_path_str

        except Exception as e:
            raise Exception(e)

    @staticmethod
    def _handle_process_result(return_code: int) -> None:
        # noinspection PyUnreachableCode
        match return_code:
            case 0:  # Нормальное завершение архивирования
                logger.info(T.successful_archiving)
            case 1:  # Завершение архивирования с не фатальными ошибками
                logger.warning(T.no_fatal_error)
            case _:  # Завершение архивации с фатальными ошибками
                logger.critical("")
                raise RuntimeError(T.fatal_error)

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
            exe_path=self.programme_path,
        )
