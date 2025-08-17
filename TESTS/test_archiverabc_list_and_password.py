import logging, pytest
from SRC.ARCHIVES.archiver_abc import Archiver
from SRC.GENERAL.constants import Constants as C


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
    import inspect

    caplog.set_level(logging.DEBUG)

    a = DummyArch()
    fn = (
        a.log_by_password_level
    )  # у некоторых реализаций метод статический/экземплярный

    # Вызываем с нужной арностью: (level, strength, entropy) или (self, level, strength, entropy)
    sig = inspect.signature(fn)
    if len(sig.parameters) == 3:
        fn(999, "S", "E")
    else:
        fn.__func__(a, 999, "S", "E")  # type: ignore[attr-defined]

    assert any(r.levelno == logging.CRITICAL for r in caplog.records)
