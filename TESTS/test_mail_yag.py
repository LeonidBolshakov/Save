
import yagmail
from yagmail.error import YagInvalidEmailAddress
from SRC.MAIL.yagmailhandler import YaGmailHandler
def test_send_email_success(monkeypatch):
    sent = {}
    class GoodSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def send(self, to=None, subject=None, contents=None):
            sent["payload"] = (to, subject, contents)
    monkeypatch.setattr(yagmail, "SMTP", GoodSMTP, raising=True)
    h = YaGmailHandler("from@example.com", "pwd", "to@example.com")
    ok = h.send_email("Subject", "Body")
    assert ok is True
    assert sent["payload"] == ("to@example.com", "Subject", "Body")
def test_send_email_invalid_address(monkeypatch):
    class BadSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def send(self, *a, **k):
            raise YagInvalidEmailAddress("bad address")
    monkeypatch.setattr(yagmail, "SMTP", BadSMTP, raising=True)
    h = YaGmailHandler("from@example.com", "pwd", "bad@example.com")
    assert h.send_email("Subj", "Body") is False
def test_send_email_generic_error(monkeypatch):
    class ErrSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def send(self, *a, **k):
            raise RuntimeError("smtp down")
    monkeypatch.setattr(yagmail, "SMTP", ErrSMTP, raising=True)
    h = YaGmailHandler("from@example.com", "pwd", "to@example.com")
    assert h.send_email("S", "B") is False
