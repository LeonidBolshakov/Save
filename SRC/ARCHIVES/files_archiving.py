from pathlib import Path
import logging

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)

# Импорт зависимостей
from SRC.ARCHIVES.search_programme import SearchProgramme
from SRC.ARCHIVES.archiver_base import CreateArch7zSpec
from SRC.GENERAL.textmessage import TextMessage as T


class FilesArchiving:
    """Класс для создания архивов.

    Обеспечивает:
    - Проверку наличия архиватора в системе
    - Создание архивов по заданным параметрам
    - Обработку ошибок архивации
    """

    def __init__(self, parameter_dict: dict) -> None:
        """Инициализация архивации.

        Args:
            parameter_dict (dict): словарь параметров

        Used parameters_dict keys:
            list_archive_file_paths: str - Путь на файл, содержащий архивируемые файлы
            archiver_name: str - Шаблон имени программы
            config_file_path: str - Путь на файл конфигурации с путями программ
            local_archive_name: str - Имя локального архива
            archiver_standard_program_paths: list[str] - Стандартные пути программы
        """
        self.parameter_dict = parameter_dict
        self._init_search()

    def _init_search(self) -> None:
        """Инициализирует поиск пути к архиватору.

        Raises:
            OSError: Если программа не найдена в системе
        """
        logger.debug(T.init_FileArchiving)

        # Получение пути к программе
        self.programme_path = SearchProgramme(
            config_file_path=self.parameter_dict.get("config_file_path")
        ).get_path(
            standard_program_paths=self.parameter_dict[
                "archiver_standard_program_paths"
            ],
            programme_template=self.parameter_dict["archiver_name"],
        )

        # Проверка наличия архиватора
        if not self.programme_path:
            logger.critical("")
            raise OSError(T.archiver_not_found)

    def make_local_archive(self) -> str:
        """Создает 7z-архив в указанной директории.

        Args:
            self

        Used parameters_dict keys
            archive_catalog: Путь к директории для архива
            password: (str) Пароль
            compression_level: (int) Уровень сжатия

        Returns:
            str: Абсолютный путь к созданному архиву

        Raises:
            RuntimeError: Если произошла ошибка при создании архива
        """
        logger.debug(T.start_create_archive)

        try:
            # Извлечение параметров
            archive_catalog = self.parameter_dict["archive_catalog"]
            password = self.parameter_dict["password"]
            compression_level = self.parameter_dict.get("compression_level", 5)

            # Формирование пути к архиву
            local_path = Path(
                archive_catalog, self.parameter_dict["local_archive_name"]
            )
            local_path_str = str(local_path)
            logger.debug(T.path_local_archive.format(local_path_str=local_path_str))

            # Создание архива
            arch_7z_spec = self.get_arch_7z_spec(
                password, compression_level, local_path_str
            )
            return_code = arch_7z_spec.create_archive()

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
            archiver_path=self.programme_path, parameters_dict=self.parameter_dict
        )
