
from SRC.GENERAL import manager_write_file as mwf
def test_write_file_dispatch(monkeypatch, tmp_path):
    called = {}
    def fake_write(local_path, remote_dir, call_back_obj):
        called["args"] = (local_path, remote_dir, call_back_obj)
        return "/disk/path/file.7z"
    monkeypatch.setattr(mwf, "write_file_to_yandex_disk", fake_write)
    p = tmp_path / "data.bin"
    p.write_bytes(b"123")
    out = mwf.write_file(str(p))
    assert out == "/disk/path/file.7z"
    assert "args" in called
