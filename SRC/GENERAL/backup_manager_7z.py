from typing import Any
from pathlib import Path
import os

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

        list_archive_file_paths = (
            Path(os.environ.get(C.ENVIRON_SETTINGS_DIRECTORY, C.SETTINGS_DIRECTORY_DEF))
            / C.LIST_NAMS_OF_ARCHIVABLE_FILES
        )

        config_file_path = self.variables.get_var(
            C.ENV_CONFIG_FILE_WITH_PROGRAM_NAME, C.CONFIG_FILE_WITH_PROGRAM_NAME_DEF
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

        return {
            C.PAR___ARCHIVER: Archiver7z,  # Ссылка на дочерний класс архиватора
            C.PAR___SEARCH_PROGRAMME: SearchProgramme7Z,  # Ссылка на класс поиска программы архиватора
            C.PAR_ARCHIVE_EXTENSION: archive_extension,
            C.PAR_ARCHIVER_NAME: archiver_name,
            C.PAR_STANDARD_PROGRAM_PATHS: archiver_standard_program_paths,
            C.PAR_COMPRESSION_LEVEL: compression_level,
            C.CONFIG_FILE_WITH_PROGRAM_NAME: config_file_path,
            C.PAR_LIST_ARCHIVE_FILE_PATHS: list_archive_file_paths,
            C.PAR_LOCAL_ARCHIVE_NAME: local_archive_name,
            C.PAR_PASSWORD: password,
        }
