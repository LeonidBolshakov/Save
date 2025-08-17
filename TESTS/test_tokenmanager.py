import requests
from SRC.YADISK.OAUTH.tokenmanager import TokenManager
from SRC.YADISK.yandexconst import YandexConstants as YC


class DummyVars:
    def __init__(self):
        self.store = {}

    def put_keyring_var(self, k, v):
        self.store[k] = v

    def put_var(self, k, v):
        self.store[k] = v

    def get_var(self, k, default=None):
        return self.store.get(k, default)


def test_save_tokens_and_get_vars(monkeypatch):
    tm = TokenManager()
    tm.variables = DummyVars()
    tm.save_tokens("acc", "ref", "12345")
    a, r, e = tm.get_vars()
    assert a == "acc" and r == "ref" and e == "12345"


def test_load_and_validate_tokens_success(monkeypatch):
    tm = TokenManager()
    tm.variables = DummyVars()
    tm.variables.put_keyring_var(YC.YANDEX_ACCESS_TOKEN, "acc")
    tm.variables.put_keyring_var(YC.YANDEX_REFRESH_TOKEN, "ref")
    tm.variables.put_var(YC.YANDEX_EXPIRES_AT, "9999999999")
    monkeypatch.setattr(
        TokenManager, "_validate_token_api", lambda self, t: True, raising=True
    )
    tokens = tm.load_and_validate_exist_tokens()
    assert tokens[YC.YANDEX_ACCESS_TOKEN] == "acc"
    assert tokens[YC.YANDEX_REFRESH_TOKEN] == "ref"
    assert tokens[YC.YANDEX_EXPIRES_AT] == "9999999999"


def test_validate_token_api_variants(monkeypatch):
    tm = TokenManager()

    # 200 OK
    class R1:
        status_code = 200

    monkeypatch.setattr(requests, "get", lambda *a, **k: R1(), raising=True)
    assert tm._validate_token_api("t") is True

    # 401/other
    class R2:
        status_code = 401

    monkeypatch.setattr(requests, "get", lambda *a, **k: R2(), raising=True)
    assert tm._validate_token_api("t") is False

    # Exception
    def boom(*a, **k):
        raise requests.RequestException("x")

    monkeypatch.setattr(requests, "get", boom, raising=True)
    assert tm._validate_token_api("t") is False
