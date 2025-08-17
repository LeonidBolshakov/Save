import pytest
from SRC.ARCHIVES.archiver_abc import Archiver
from SRC.GENERAL.constants import Constants as C


class DummyArchiver(Archiver):
    def get_cmd_archiver(
        self, archiver_program: str, parameters_dict: dict[str, object]
    ) -> list[str]:
        return [archiver_program, "a"]


def test_check_arch_exists_raises(tmp_path):
    a = DummyArchiver()
    arch_path = tmp_path / "exists.7z"
    arch_path.write_text("x")
    with pytest.raises((FileExistsError, KeyError)):
        a._check_all_params(
            {
                C.PAR_ARCHIVE_PATH: str(arch_path),
                C.PAR_LIST_ARCHIVE_FILE_PATHS: str(tmp_path / "list.txt"),
            }
        )


def test_check_list_file_raises(tmp_path):
    a = DummyArchiver()
    params = {
        C.PAR_ARCHIVE_PATH: str(tmp_path / "out.7z"),
        C.PAR_LIST_ARCHIVE_FILE_PATHS: str(tmp_path / "missing.txt"),
    }
    with pytest.raises(FileNotFoundError):
        a._check_all_params(params)
