
import subprocess as _sp
from SRC.ARCHIVES.search_programme_7z import SearchProgramme7Z

def test_exec_success(monkeypatch, tmp_path):
    class R: returncode = 0; stderr = b""
    monkeypatch.setattr(_sp, "run", lambda *a, **k: R(), raising=True)
    s = SearchProgramme7Z()
    assert s.test_programme_execution("7z.exe") is True

def test_exec_failure(monkeypatch):
    class R: returncode = 2; stderr = b"err"
    monkeypatch.setattr(_sp, "run", lambda *a, **k: R(), raising=True)
    s = SearchProgramme7Z()
    assert s.test_programme_execution("7z.exe") is False

def test_exec_exception(monkeypatch):
    def boom(*a, **k): raise RuntimeError("crash")
    monkeypatch.setattr(_sp, "run", boom, raising=True)
    s = SearchProgramme7Z()
    assert s.test_programme_execution("7z.exe") is False
