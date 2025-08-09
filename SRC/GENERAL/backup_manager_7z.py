from typing import Any

from SRC.ARCHIVES.archiver7z import Archiver7z
from SRC.ARCHIVES.search_programme_7z import SearchProgramme7Z
from SRC.GENERAL.backup_manager_abc import BackupManager
from SRC.GENERAL.constants import Constants as C


class BackupManager7z(BackupManager):
    """Настройка базового класса - BackupManager"""

    def get_parameters_dict(self) -> dict[str, Any]:
        """
        Замена метода get_parameters_dict в базовом классе.
        Функция формирует и возвращает словарь параметров
        Значения для словаря берутся из переменных окружения, а если их там нет, то берутся значения по умолчанию

        :parameter: ---

        :returns: словарь параметров
        :rtype: dict[str, Any]
        """

        archiver_name = self.variables.get_var(
            C.ENV_FULL_ARCHIVER_NAME, C.FULL_NAME_SEVEN_Z
        )
        list_archive_file_paths = self.variables.get_var(
            C.ENV_LIST_PATH_TO_LIST_OF_ARCHIVABLE_FILES,
            C.LIST_PATH_TO_LIST_OF_ARCHIVABLE_FILES_DEF,
        )

        full_archiver_name = self.variables.get_var(
            C.ENV_FULL_ARCHIVER_NAME, C.FULL_NAME_SEVEN_Z
        )
        config_file_path = self.variables.get_var(
            C.ENV_CONFIG_FILE_WITH_PROGRAM_NAME, C.CONFIG_FILE_WITH_PROGRAM_NAME
        )

        local_archive_name = self.variables.get_var(
            C.ENV_LOCAL_ARCHIVE_FILE_NAME, C.LOCAL_ARCHIVE_FILE_NAME_DEF
        )

        password = self.variables.get_var(C.ENV_PASSWORD_ARCHIVE)
        compression_level = self.variables.get_var(
            C.ENV_SEVEN_Z_COMPRESSION_LEVEL, C.SEVEN_Z_COMPRESSION_LEVEL_DEF
        )

        archiver_standard_program_paths = self.variables.get_var(
            C.ENV_ARCHIVER_STANDARD_PROGRAM_PATHS, C.SEVEN_Z_STANDARD_PATHS
        )

        archive_extension = self.variables.get_var(
            C.ENV_LOCAL_ARCHIVE_SUFFIX, C.LOCAL_ARCHIVE_SUFFIX_DEF
        )

        Archiver = Archiver7z  # Ссылка на дочерний класс архиватора
        search_programme_class = (
            SearchProgramme7Z  # Ссылка на класс поиска программы архиватора
        )

        return {
            "Archiver": Archiver,
            "SearchProgramme": search_programme_class,
            "archive_extension": archive_extension,
            "archiver_name": archiver_name,
            "full_archiver_name": full_archiver_name,
            "archiver_standard_program_paths": archiver_standard_program_paths,
            "compression_level": compression_level,
            "config_file_path": config_file_path,
            "list_archive_file_paths": list_archive_file_paths,
            "local_archive_name": local_archive_name,
            "password": password,
        }
