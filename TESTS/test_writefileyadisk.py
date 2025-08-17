
import SRC.YADISK.writefileyandexdisk as wfy
def test_write_file_success(monkeypatch):
    class FakeDisk:
        def __init__(self, remote_dir, call_back_obj): pass
        def write_file_fast(self, local_path): return "/disk/ok/file.7z"
    monkeypatch.setattr(wfy, "YandexDisk", FakeDisk, raising=True)
    out = wfy.write_file_to_yandex_disk("C:/file.7z", "/disk", call_back_obj=object())
    assert out == "/disk/ok/file.7z"
def test_write_file_failure(monkeypatch):
    class FakeDisk:
        def __init__(self, remote_dir, call_back_obj): pass
        def write_file_fast(self, local_path): return ""
    monkeypatch.setattr(wfy, "YandexDisk", FakeDisk, raising=True)
    import pytest
    with pytest.raises(RuntimeError):
        wfy.write_file_to_yandex_disk("C:/file.7z", "/disk", call_back_obj=object())
