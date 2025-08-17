
from types import SimpleNamespace
from SRC.YADISK.uploader_yadisk import UploaderToYaDisk
def test_retryable_status():
    assert UploaderToYaDisk._is_retryable_status(429) is True
    assert UploaderToYaDisk._is_retryable_status(500) is True
    assert UploaderToYaDisk._is_retryable_status(504) is True
    assert UploaderToYaDisk._is_retryable_status(200) is False
def test_md5_calc_and_remote_meta(tmp_path):
    f = tmp_path / "data.bin"
    f.write_bytes(b"abc")
    up = UploaderToYaDisk(ya_disk=SimpleNamespace(), remote_path="/disk/file")
    md5 = up.calculate_md5(str(f))
    assert md5 == "900150983cd24fb0d6963f7d28e17f72"
    up.ya_disk = SimpleNamespace(get_meta=lambda path, fields=None: SimpleNamespace(md5="abc123"))
    assert up.get_remote_md5_yadisk("/p") == "abc123"
    up.ya_disk = SimpleNamespace(get_meta=lambda path, fields=None: {"md5": "def456"})
    assert up.get_remote_md5_yadisk("/p") == "def456"
    up.ya_disk = SimpleNamespace(get_meta=lambda path, fields=None: SimpleNamespace())
    assert up.get_remote_md5_yadisk("/p") is None
