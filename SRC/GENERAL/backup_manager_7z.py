from typing import Any

from SRC.ARCHIVES.archiver7z import Archiver7z
from SRC.ARCHIVES.search_programme_7z import SearchProgramme7Z
from SRC.GENERAL import paths_win
from SRC.GENERAL.backup_manager_abc import BackupManager
from SRC.GENERAL.constants import Constants as C


class BackupManager7z(BackupManager):
    """Настройка базового класса - BackupManager"""

    def get_parameters_dict(self) -> dict[str, Any]:
        """
        Замена метода get_parameters_dict в базовом классе.
        Формирует словарь параметров для BackupManager.
        """

        list_archive_file_paths = paths_win.get_list_archive_file_paths()

        archiver_name = self.variables.get_var(
            C.ENV_FULL_ARCHIVER_NAME, C.FULL_NAME_SEVEN_Z
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
            C.PAR___ARCHIVER: Archiver7z,
            C.PAR___SEARCH_PROGRAMME: SearchProgramme7Z,
            C.PAR_ARCHIVE_EXTENSION: archive_extension,
            C.PAR_ARCHIVER_NAME: archiver_name,
            C.PAR_STANDARD_PROGRAM_PATHS: archiver_standard_program_paths,
            C.PAR_COMPRESSION_LEVEL: compression_level,
            C.CONFIG_FILE_WITH_PROGRAM_NAME: config_file_path,
            C.PAR_LIST_ARCHIVE_FILE_PATHS: list_archive_file_paths,
            C.PAR_LOCAL_ARCHIVE_NAME: local_archive_name,
            C.PAR_PASSWORD: password,
        }
