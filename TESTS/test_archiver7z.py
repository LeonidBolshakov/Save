
from SRC.ARCHIVES.archiver7z import Archiver7z
from SRC.GENERAL.constants import Constants as C
def _params(tmp_path):
    return {
        C.PAR_ARCHIVER_NAME: "7z.exe",
        C.PAR_ARCHIVE_PATH: str(tmp_path / "out.7z"),
        C.PAR_COMPRESSION_LEVEL: 5,
        C.PAR_LIST_ARCHIVE_FILE_PATHS: str(tmp_path / "list.txt"),
        C.PAR_PASSWORD: "pass",
        C.PAR_ARCHIVE_EXTENSION: ".7z",
    }
def test_build_cmd_includes_flags(tmp_path):
    a = Archiver7z()
    p = _params(tmp_path)
    cmd = a.get_cmd_archiver("C:/Program Files/7-Zip/7z.exe", p)
    assert cmd[0].endswith("7z.exe")
    assert "a" in cmd
    assert any(s.startswith("-mx=") for s in cmd)
    assert any(s.startswith("-p") for s in cmd)
    assert f"@{p[C.PAR_LIST_ARCHIVE_FILE_PATHS]}" in cmd
def test_build_cmd_sfx_when_exe(tmp_path):
    a = Archiver7z()
    p = _params(tmp_path)
    p[C.PAR_ARCHIVE_EXTENSION] = ".exe"
    cmd = a.get_cmd_archiver("C:/Program Files/7-Zip/7z.exe", p)
    assert "-sfx" in cmd
