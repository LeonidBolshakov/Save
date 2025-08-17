from SRC.ARCHIVES.archiver7z import Archiver7z
from SRC.GENERAL.constants import Constants as C


def _params(tmp_path, level):
    return {
        C.PAR_ARCHIVER_NAME: "7z.exe",
        C.PAR_ARCHIVE_PATH: str(tmp_path / "out.7z"),
        C.PAR_COMPRESSION_LEVEL: level,
        C.PAR_LIST_ARCHIVE_FILE_PATHS: str(tmp_path / "list.txt"),
        C.PAR_PASSWORD: "pass",
        C.PAR_ARCHIVE_EXTENSION: ".7z",
    }


def _mx_in_cmd(cmd):
    for s in cmd:
        if s.startswith("-mx="):
            return s
    return ""


def test_check_compression_level_via_cmd_valid(tmp_path):
    a = Archiver7z()
    for lvl in (0, 5, 9):
        cmd = a.get_cmd_archiver(
            "C:/Program Files/7-Zip/7z.exe", _params(tmp_path, lvl)
        )
        assert _mx_in_cmd(cmd) == f"-mx={lvl}"


def test_check_compression_level_via_cmd_invalid(tmp_path):
    a = Archiver7z()
    for lvl in (-1, 10, "bad"):  # type: ignore
        cmd = a.get_cmd_archiver(
            "C:/Program Files/7-Zip/7z.exe", _params(tmp_path, lvl)
        )
        assert _mx_in_cmd(cmd) == f"-mx={C.SEVEN_Z_COMPRESSION_LEVEL_DEF}"
