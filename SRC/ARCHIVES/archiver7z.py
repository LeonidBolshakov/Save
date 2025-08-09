import logging
from typing import Any

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)

# Импорт зависимостей
from SRC.ARCHIVES.archiver_abc import Archiver, BacupManagerArchiver
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class Archiver7z(Archiver, BacupManagerArchiver):
    """Класс для создания архивов 7z.

    Обеспечивает:
    - Подготовку командной строки для создания архива 7z
    """

    def __init__(self, parameter_dict: dict[str, Any]) -> None:
        """Инициализация архивации.

        Args:
            parameter_dict (dict): словарь параметров

        Использует следующие parameters_dict ключи (включая базовый класс) :
            Archiver: - Дочерний класс архиватора. Например, Archiver7z
            SearchProgramme: - Дочерний класс для поиска программы. Например, SearchProgramme7Z
            archive_extension: str - Расширение архива. Например, '.exe'
            archiver_name: str - Шаблон имени программы
            archiver_standard_program_paths: list[str] - Стандартные пути программы (Опционально)
            compression_level: int Уровень сжатия  (опционально) [0, 9]. 0- без сжатия, 9 - ультра сжатие
            config_file_path: str - Путь на файл конфигурации с путями программ
            list_archive_file_paths: str - Путь на файл, содержащий архивируемые файлы
            local_archive_name: str - Имя локального архива
            password: str - Пароль (опционально)

        """
        super().__init__(parameter_dict)
        self.parameter_dict = parameter_dict

    def _get_cmd_archiver(self, archiver_program: str) -> list[str]:
        """
        Формирует команду для выполнения архивации с помощью 7z.

        Parameters:
            archiver_program: str Путь на программу архивации

        Returns:
            list[str]: Список аргументов команды для subprocess.run

        Note:
            Пароль в логах маскируется звездочками для безопасности
        """
        compression_level: int = self.parameters_dict["compression_level"]
        compression_level = self._check_validate_of_compression(
            compression_level=compression_level
        )
        archive_path: str = self.parameters_dict["archive_path"]
        password: str = self.parameters_dict["password"]
        list_archive_file_paths: str = self.parameters_dict["list_archive_file_paths"]
        archive_extension: str = self.parameters_dict["archive_extension"]
        cmd = [
            archiver_program,  # Путь к программе архиватору
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
    def _check_validate_of_compression(compression_level: int) -> int:
        """
        Проверка параметра "Уровень компрессии". Параметр должен быть целым число в сегменте [0,9]
        :param compression_level: (int) - Уровень компрессии
        :return: None
        """
        if not isinstance(compression_level, int):
            logger.warning(T.error_in_compression_level.format(level=compression_level))
            return C.SEVEN_Z_COMPRESSION_LEVEL_DEF

        if 0 <= compression_level <= 9:
            return compression_level

        logger.warning(T.error_in_compression_level.format(level=compression_level))
        return C.SEVEN_Z_COMPRESSION_LEVEL_DEF
