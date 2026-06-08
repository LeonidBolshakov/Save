import logging, pytest
from src.ARCHIVES.archiver_abc import Archiver
from src.GENERAL.constants import Constants as C


class DummyArch(Archiver):
    def get_cmd_archiver(
        self, archiver_program: str, parameters_dict: dict[str, str]
    ) -> list[str]:
        return ["7z.exe"]


def test_check_list_file_missing_raises(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    p = {C.PAR_LIST_ARCHIVE_FILE_PATHS: str(tmp_path / "missing.txt")}
    with pytest.raises(FileNotFoundError):
        Archiver._check_list_file(p)


def test_check_list_file_ok(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    lf = tmp_path / "list.txt"
    lf.write_text("C:/data/file1.txt\n")
    Archiver._check_list_file({C.PAR_LIST_ARCHIVE_FILE_PATHS: str(lf)})


def test_classify_strength_all_bands():
    f = Archiver.classify_strength
    assert f(0.0)[1] == logging.WARNING
    assert f(0.3)[1] == logging.INFO
    assert f(0.6)[1] == logging.DEBUG
    assert f(0.9)[1] == logging.DEBUG


def test_classify_entropy_all_bands():
    f = Archiver.classify_entropy
    assert f(10)[1] == logging.WARNING
    assert f(30)[1] == logging.INFO
    assert f(60)[1] == logging.DEBUG
    assert f(85)[1] == logging.DEBUG


def test_message_about_password_and_log_levels(caplog):
    caplog.set_level(logging.DEBUG)

    a = DummyArch()

    # Вызываем с нужной арностью: (level, strength, entropy) или (self, level, strength, entropy)
    a.log_by_password_level(999, "S", "E")

    assert any(
        record.levelno == logging.CRITICAL for record in caplog.records
    ), "Ожидалась хотя бы одна запись лога уровня CRITICAL"
