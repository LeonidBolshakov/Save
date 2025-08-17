
import logging
from SRC.ARCHIVES.archiver_abc import Archiver
class DummyArchiver(Archiver):
    def get_cmd_archiver(self, archiver_program: str, parameters_dict: dict[str, object]) -> list[str]:
        return [archiver_program, "a"]
def test_password_classification_and_logging(caplog):
    a = DummyArchiver()
    caplog.set_level(logging.DEBUG)
    a.log_by_password_level(logging.WARNING, "very_weak", "unreliable")
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    caplog.clear()
    a.log_by_password_level(logging.DEBUG, "medium", "high")
    assert any(r.levelno == logging.DEBUG for r in caplog.records)
def test_mask_password_in_cmd():
    a = DummyArchiver()
    cmd = ["7z.exe", "-ppass123", "a"]
    masked = a._mask_password_in_cmd(cmd, "pass123")
    assert any(s.startswith("-p") for s in masked)
    assert all("pass123" not in s for s in masked)
