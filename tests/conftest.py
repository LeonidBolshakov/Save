import os, types, sys, pytest
import webbrowser

os.environ["TESTING"] = "1"


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    import socket

    def guard(*args, **kwargs):
        raise RuntimeError("Network disabled in tests")

    monkeypatch.setattr(socket, "create_connection", guard, raising=True)
    monkeypatch.setattr(
        socket,
        "socket",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("Network disabled")),
        raising=True,
    )
    yield


@pytest.fixture(autouse=True)
def _dummy_keyring(monkeypatch):
    store = {}

    class DummyKeyring:
        def set_password(self, app, name, value):
            store[(app, name)] = value

        def get_password(self, app, name):
            return store.get((app, name))

        def delete_password(self, app, name):
            store.pop((app, name), None)

    sys.modules["keyring"] = types.SimpleNamespace(
        set_password=DummyKeyring().set_password,
        get_password=DummyKeyring().get_password,
        delete_password=DummyKeyring().delete_password,
    )
    yield


@pytest.fixture(autouse=True)
def _dummy_yadisk(monkeypatch):
    # exceptions namespace
    class YaDiskError(Exception): ...

    class UnauthorizedError(YaDiskError): ...

    class BadRequestError(YaDiskError): ...

    exc_mod = types.SimpleNamespace(
        YaDiskError=YaDiskError,
        UnauthorizedError=UnauthorizedError,
        BadRequestError=BadRequestError,
    )
    sys.modules["yadisk.exceptions"] = exc_mod

    # minimal client
    class _DummyClient:
        def __init__(self, *a, **k):
            pass

        def check_token(self, token=None):
            return True

        def exists(self, path):
            return True

        def mkdir(self, path):
            return None

        def listdir(self, path):
            return []

        def get_upload_link(self, path):
            return types.SimpleNamespace(href="http://example")

        def upload(self, local_path, remote_path, overwrite=True):
            return None

        def get_meta(self, path, fields=None):
            return {}

    sys.modules["yadisk"] = types.SimpleNamespace(
        YaDisk=_DummyClient, exceptions=exc_mod
    )
    yield


@pytest.fixture(autouse=True)
def _dummy_yagmail(monkeypatch):
    class DummySMTP:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def send(self, to=None, subject=None, contents=None):
            return {"to": to, "subject": subject, "contents": contents}

    class YagAddressError(Exception):
        pass

    class YagInvalidEmailAddress(Exception):
        pass

    sys.modules["yagmail"] = types.SimpleNamespace(SMTP=DummySMTP)
    sys.modules["yagmail.error"] = types.SimpleNamespace(
        YagAddressError=YagAddressError, YagInvalidEmailAddress=YagInvalidEmailAddress
    )
    yield


@pytest.fixture(autouse=True)
def _stub_browser(monkeypatch):
    opened = {"url": None}

    def fake_open(url, *a, **k):
        opened["url"] = url
        return True

    monkeypatch.setattr(webbrowser, "open", fake_open, raising=True)
    monkeypatch.setattr(webbrowser, "open_new", fake_open, raising=True)
    monkeypatch.setattr(webbrowser, "open_new_tab", fake_open, raising=True)
    return opened
