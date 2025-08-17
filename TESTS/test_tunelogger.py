
import logging
from SRC.LOGGING.tunelogger import TuneLogger
class DummyVars:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
    def get_var(self, name, default):
        if "FILE_LOG_NAME" in name:
            return str(self.tmp / "log.txt")
        return default
def test_tunelogger_setup_adds_handlers(tmp_path, monkeypatch):
    t = TuneLogger()
    monkeypatch.setattr(t, "variables", DummyVars(tmp_path), raising=True)
    t.setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 2
    t._remove_loging()
    assert len(logging.getLogger().handlers) == 0
