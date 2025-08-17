import logging
import pytest
from SRC.ARCHIVES.archiver7z import Archiver7z
from SRC.GENERAL.constants import Constants as C


def _p(tmp_path):
    return {
        C.PAR_ARCHIVER_NAME: "7z.exe",
        C.PAR_ARCHIVE_PATH: str(tmp_path / "out.7z"),
        # C.PAR_COMPRESSION_LEVEL intentionally omitted
        C.PAR_LIST_ARCHIVE_FILE_PATHS: str(tmp_path / "list.txt"),
        C.PAR_PASSWORD: "pass",
        # C.PAR_ARCHIVE_EXTENSION present in first test
        C.PAR_ARCHIVE_EXTENSION: ".7z",
    }


def test_cmd_uses_default_level_when_missing(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    a = Archiver7z()
    params = _p(tmp_path)
    cmd = a.get_cmd_archiver("C:/Program Files/7-Zip/7z.exe", params)
    assert any(s.startswith("-mx=") for s in cmd)


def test_missing_extension_raises(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    a = Archiver7z()
    params = _p(tmp_path)
    params.pop(C.PAR_ARCHIVE_EXTENSION, None)
    with pytest.raises(KeyError):
        a.get_cmd_archiver("C:/Program Files/7-Zip/7z.exe", params)
