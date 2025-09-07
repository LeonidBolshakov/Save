import logging
from typing import Any

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)

# Импорт зависимостей
from SRC.ARCHIVES.archiver_abc import Archiver, BackupManagerArchiver
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class Archiver7z(Archiver, BackupManagerArchiver):
    """Класс для создания архивов 7z.

    Обеспечивает:
    - Подготовку командной строки для создания архива 7z
    """

    def get_cmd_archiver(
        self, archiver_program: str, parameters_dict: dict[str, Any]
    ) -> list[str]:
        """
        Формирует команду для выполнения архивации с помощью 7z.

        Parameters:
            archiver_program: str Путь на программу архивации
            parameters_dict: dict[str, Any] - Словарь параметров

        Returns:
            list[str]: Список аргументов команды для subprocess.run

        Note:
            Пароль в логах маскируется звездочками для безопасности
        """
        try:
            compression_level: int = parameters_dict[C.PAR_COMPRESSION_LEVEL]
        except KeyError as e:
            logger.warning(
                T.error_parameter_archiver.format(param=C.PAR_COMPRESSION_LEVEL)
            )
            compression_level = C.SEVEN_Z_COMPRESSION_LEVEL_DEF

        compression_level = self._check_validate_of_compression(
            compression_level=compression_level
        )
        archive_path = parameters_dict[C.PAR_ARCHIVE_PATH]
        password = parameters_dict.get(C.PAR_PASSWORD)
        list_archive_file_paths: str = parameters_dict[C.PAR_LIST_ARCHIVE_FILE_PATHS]
        try:
            archive_extension: str = parameters_dict[C.PAR_ARCHIVE_EXTENSION]
        except KeyError as e:
            logger.critical(
                T.error_parameter_archiver.format(param=C.PAR_ARCHIVE_EXTENSION)
            )
            raise KeyError from e

        return self._cmd_archiver(
            archiver_program,
            password,
            archive_extension,
            compression_level,
            archive_path,
            list_archive_file_paths,
        )

    @staticmethod
    def _cmd_archiver(
        archiver_program: str,
        password: str | None,
        archive_extension: str,
        compression_level: int,
        archive_path: str,
        list_archive_file_paths: str,
    ) -> list[str]:
        """Собирает команду для 7z с валидацией параметров."""
        return [
            archiver_program,
            "a",
            *([f"-p{password}"] if password else []),
            "-mhe=on",
            *(["-sfx"] if archive_extension == ".exe" else []),
            f"-mx={compression_level}",
            archive_path,
            f"@{list_archive_file_paths}",
            "-spf",
            "-bso0",
            "-bsp0",
        ]

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
