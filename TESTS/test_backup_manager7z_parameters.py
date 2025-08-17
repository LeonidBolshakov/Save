
from SRC.GENERAL.backup_manager_7z import BackupManager7z
from SRC.GENERAL.constants import Constants as C
def test_parameters_dict_has_core_keys():
    bm = BackupManager7z()
    d = bm.get_parameters_dict()
    for k in [C.PAR___ARCHIVER, C.PAR___SEARCH_PROGRAMME, C.PAR_ARCHIVE_EXTENSION,
              C.PAR_ARCHIVER_NAME, C.PAR_STANDARD_PROGRAM_PATHS, C.PAR_COMPRESSION_LEVEL,
              C.CONFIG_FILE_WITH_PROGRAM_NAME, C.PAR_LIST_ARCHIVE_FILE_PATHS,
              C.PAR_LOCAL_ARCHIVE_NAME, C.PAR_PASSWORD]:
        assert k in d
