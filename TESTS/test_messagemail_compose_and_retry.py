import types, logging
import SRC.MAIL.messagemail as mm
from SRC.MAIL.messagemail import MessageMail


class DummyMax:
    def __init__(self, last_time, level, path):
        self._t, self._l, self._p = last_time, level, path

    def get_highest_level(self):
        return self._l

    def get_last_time(self):
        return self._t

    def get_remote_archive_path(self):
        return self._p


def test_compose_info_and_send(monkeypatch):
    monkeypatch.setattr(
        mm,
        "MaxLevelHandler",
        lambda: DummyMax(1000.0, logging.INFO, "/p.7z"),
        raising=True,
    )
    m = MessageMail()
    m.email_handler = types.SimpleNamespace(send_email=lambda s, c: True)
    assert m.compose_and_send_email() is True


def test_compose_warning_and_error_paths(monkeypatch):
    monkeypatch.setattr(
        mm,
        "MaxLevelHandler",
        lambda: DummyMax(1000.0, logging.WARNING, "/p.7z"),
        raising=True,
    )
    m = MessageMail()
    m.email_handler = types.SimpleNamespace(send_email=lambda s, c: True)
    assert m.compose_and_send_email() is True
    monkeypatch.setattr(
        mm,
        "MaxLevelHandler",
        lambda: DummyMax(1000.0, logging.ERROR, "/p.7z"),
        raising=True,
    )
    m = MessageMail()
    m.email_handler = types.SimpleNamespace(send_email=lambda s, c: True)
    assert m.compose_and_send_email() is True


def test_retry_logic_on_exception(monkeypatch):
    monkeypatch.setattr(mm.time, "sleep", lambda s: None, raising=True)
    monkeypatch.setattr(
        mm,
        "MaxLevelHandler",
        lambda: DummyMax(1000.0, logging.INFO, "/p.7z"),
        raising=True,
    )
    m = MessageMail()
    attempts = {"n": 0}

    def sender(subject, content):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise RuntimeError("fail once")
        return True

    m.email_handler = types.SimpleNamespace(send_email=sender)
    assert m.compose_and_send_email() is True
    assert attempts["n"] == 2
