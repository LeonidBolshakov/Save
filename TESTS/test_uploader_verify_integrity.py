from types import SimpleNamespace
import pytest
from SRC.YADISK.uploader_yadisk import UploaderToYaDisk, HashMismatchError


def _mk(md5_value):
    # ya_disk.get_meta вернёт объект с нужным md5
    return UploaderToYaDisk(
        ya_disk=SimpleNamespace(
            get_meta=lambda path, fields=None: SimpleNamespace(md5=md5_value)
        ),
        remote_path="/disk/file",
    )


def test_verify_integrity_ok(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"abc")  # md5=900150983cd24fb0d6963f7d28e17f72
    up = _mk("900150983cd24fb0d6963f7d28e17f72")
    # не должно бросать
    up._verify_integrity(str(f), "/disk/file")  # type: ignore[attr-defined]


def test_verify_integrity_mismatch(tmp_path):
    f = tmp_path / "b.bin"
    f.write_bytes(b"abc")
    up = _mk("deadbeef")
    with pytest.raises(HashMismatchError):
        up._verify_integrity(str(f), "/disk/file")  # type: ignore[attr-defined]
