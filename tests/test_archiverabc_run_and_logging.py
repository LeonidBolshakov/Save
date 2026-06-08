import types, pytest
from src.ARCHIVES.archiver_abc import Archiver
from src.GENERAL.constants import Constants as C


class DummyArch(Archiver):
    def get_cmd_archiver(
        self, archiver_program: str, parameters_dict: dict[str, str]
    ) -> list[str]:
        return ["7z.exe"]


def test_get_archive_path_builds_path():
    a = DummyArch()
    p = {C.PAR_ARCHIVE_DIR: "/tmp", C.PAR_LOCAL_ARCHIVE_NAME: "x.7z"}
    assert a.get_archive_path(p).endswith("x.7z")


def test_run_archiver_returncodes_and_masks_password(
    monkeypatch,
    caplog,
):
    a = DummyArch()
    # rc==0 -> успех
    monkeypatch.setattr(
        a,
        "_run_archive_process",
        lambda *args, **kwargs: types.SimpleNamespace(returncode=0, stderr=""),
        raising=True,
    )
    assert a._run_archiver(["x"], "/tmp/x.7z", "password") is True
    assert "password" not in caplog.text

    # rc==1 -> замечены ошибки
    monkeypatch.setattr(
        a,
        "_run_archive_process",
        lambda *args, **kwargs: types.SimpleNamespace(returncode=1, stderr="warn"),
        raising=True,
    )
    result = a._run_archiver(["x"], "/tmp/x.7z", "password")
    assert result is True
    assert "Ошибка при выполнении процесса ['x']" in caplog.text
    assert "warn" in caplog.text
    assert "password" not in caplog.text

    # rc > 1 ->
    monkeypatch.setattr(
        a,
        "_run_archive_process",
        lambda *args, **kwargs: types.SimpleNamespace(returncode=2, stderr="err"),
        raising=True,
    )
    result = a._run_archiver(["x"], "/tmp/x.7z", "password")
    assert result is False
    assert "Ошибка при выполнении процесса ['x']" in caplog.text
    assert "err" in caplog.text
    assert "password" not in caplog.text

    # исключение из процесса → RuntimeError
    def boom(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(a, "_run_archive_process", boom, raising=True)
    with pytest.raises(RuntimeError):
        a._run_archiver(["x"], "/tmp/x.7z", "password")
    assert "password" not in caplog.text
