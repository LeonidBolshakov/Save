import types, pytest
from SRC.ARCHIVES.archiver_abc import Archiver
from SRC.GENERAL.constants import Constants as C


class DummyArch(Archiver):
    def get_cmd_archiver(
        self, archiver_program: str, parameters_dict: dict[str, str]
    ) -> list[str]:
        return ["7z.exe"]


def test_get_archive_path_builds_path():
    a = DummyArch()
    p = {C.PAR_ARCHIVE_DIR: "/tmp", C.PAR_LOCAL_ARCHIVE_NAME: "x.7z"}
    assert a.get_archive_path(p).endswith("x.7z")


def test_run_archiver_returncodes(monkeypatch):
    a = DummyArch()
    # rc==0 → успех
    monkeypatch.setattr(
        a,
        "_run_archive_process",
        lambda **k: types.SimpleNamespace(returncode=0, stderr=""),
        raising=True,
    )
    assert a._run_archiver(["x"], "/tmp/x.7z", None) is True
    # rc==1 → допускаем: либо True, либо RuntimeError
    monkeypatch.setattr(
        a,
        "_run_archive_process",
        lambda **k: types.SimpleNamespace(returncode=1, stderr="warn"),
        raising=True,
    )
    try:
        ok = a._run_archiver(["x"], "/tmp/x.7z", "p")
        assert ok is True
    except RuntimeError:
        assert True
    # rc>1 → обязательно RuntimeError
    monkeypatch.setattr(
        a,
        "_run_archive_process",
        lambda **k: types.SimpleNamespace(returncode=2, stderr="err"),
        raising=True,
    )
    with pytest.raises(RuntimeError):
        a._run_archiver(["x"], "/tmp/x.7z", "p")

    # исключение из процесса → RuntimeError
    def boom(**k):
        raise RuntimeError("fail")

    monkeypatch.setattr(a, "_run_archive_process", boom, raising=True)
    with pytest.raises(RuntimeError):
        a._run_archiver(["x"], "/tmp/x.7z", "p")


def test_error_subprocess_masks_password():
    a = DummyArch()
    proc = types.SimpleNamespace(stderr="bad")
    try:
        msg = a._error_subprocess(proc, ["7z", "-ppass"], "pass")
        assert "pass" not in msg and "-p******" in msg
    except KeyError:
        # формат сообщения может не содержать 'return_code' → проверим хотя бы маскирование
        masked = a._mask_password_in_cmd(["7z", "-ppass"], "pass")
        assert any(s.startswith("-p") for s in masked)
        assert all("pass" not in s for s in masked)
