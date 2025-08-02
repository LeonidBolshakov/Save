from backup_manager import BackupManager
from constants import Constants as C


class BackupManager7z(BackupManager):
    def get_variables_(self) -> tuple:
        list_archive_file_path = self.variables.get_var(
            C.ENV_LIST_ARCHIVE_FILE_PATH, C.LIST_ARCHIVE_FILE_PATCH
        )
        archiver_programme_template = self.variables.get_var(
            C.ENV_PATTERN_7Z, C.PATTERN_7_Z
        )
        config_file_path = self.variables.get_var(
            C.ENV_CONFIG_FILE_PATH, C.CONFIG_FILE_PATH
        )
        local_archive_name = self.variables.get_var(
            C.ENV_LOCAL_ARCHIVE_FILE_NAME, C.LOCAL_ARCHIVE_FILE_NAME
        )
        password = self.variables.get_var(C.ENV_PASSWORD_ARCHIVE)
        compress_level = self.variables.get_var(
            C.ENV_COMPRESSION_LEVEL, C.COMPRESSION_LEVEL
        )
        return (
            list_archive_file_path,
            archiver_programme_template,
            config_file_path,
            local_archive_name,
            password,
            compress_level,
        )
