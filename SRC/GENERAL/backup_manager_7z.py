from SRC.GENERAL.backup_manager import BackupManager
from SRC.GENERAL.constants import Constants as C


class BackupManager7z(BackupManager):
    def get_parameters_dict(self) -> dict:
        list_archive_file_paths = self.variables.get_var(
            C.ENV_LIST_ARCHIVE_FILE_PATH, C.LIST_ARCHIVE_FILE_PATCH
        )
        archiver_name = self.variables.get_var(C.ENV_PATTERN_7Z, C.PATTERN_PROGRAMME)
        config_file_path = self.variables.get_var(
            C.ENV_CONFIG_FILE_PATH, C.CONFIG_FILE_PATH
        )
        local_archive_name = self.variables.get_var(
            C.ENV_LOCAL_ARCHIVE_FILE_NAME, C.LOCAL_ARCHIVE_FILE_NAME
        )
        password = self.variables.get_var(C.ENV_PASSWORD_ARCHIVE)
        compression_level = self.variables.get_var(
            C.ENV_COMPRESSION_LEVEL, C.COMPRESSION_LEVEL
        )
        archiver_standard_program_paths = self.variables.get_var(
            C.ENV_STANDARD_PROGRAM_PATHS, C.STANDARD_7Z_PATHS
        )
        archive_extension = self.variables.get_var(
            C.ENV_ARCHIVE_SUFFIX, C.ARCHIVE_SUFFIX
        )
        return {
            "list_archive_file_paths": list_archive_file_paths,
            "archiver_name": archiver_name,
            "config_file_path": config_file_path,
            "local_archive_name": local_archive_name,
            "password": password,
            "compression_level": compression_level,
            "archiver_standard_program_paths": archiver_standard_program_paths,
            "archive_extension": archive_extension,
        }
