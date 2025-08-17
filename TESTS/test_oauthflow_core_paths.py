import types, pytest
from SRC.YADISK.OAUTH.oauthflow import OAuthFlow
from SRC.YADISK.yandexconst import YandexConstants as YC


def _flow():
    f = OAuthFlow()
    return f


def test_token_in_memory_paths(monkeypatch):
    f = _flow()
    f.access_token = "A"
    monkeypatch.setattr(f, "is_token_expired", lambda: False, raising=True)
    assert f.token_in_memory() == "A"
    monkeypatch.setattr(f, "is_token_expired", lambda: True, raising=True)
    assert f.token_in_memory() is None


def test_loaded_tokens_sets_state(monkeypatch):
    f = _flow()
    tokens = {
        YC.YANDEX_ACCESS_TOKEN: "A",
        YC.YANDEX_REFRESH_TOKEN: "R",
        YC.YANDEX_EXPIRES_AT: "1000",
    }
    f.token_manager = types.SimpleNamespace(
        load_and_validate_exist_tokens=lambda: tokens
    )
    out = f.loaded_tokens()
    assert (
        out is tokens
        and f.access_token == "A"
        and f.refresh_token == "R"
        and f._token_expires_at == 1000.0
    )


def test_return_tokens_error_paths(monkeypatch):
    f = _flow()

    class BadJSON:
        status_code = 200

        def json(self):
            raise ValueError("bad")

        text = "oops"

    with pytest.raises(Exception):
        f.return_tokens(BadJSON())

    class NotDict:
        status_code = 200

        def json(self):
            return ["A", "B"]

        text = "[]"

    with pytest.raises(Exception):
        f.return_tokens(NotDict())


def test_get_port_invalid(monkeypatch):
    # Подменяем EnvironmentVariables внутри модуля на заглушку
    import SRC.YADISK.OAUTH.oauthflow as of

    class V:
        def get_var(self, name, default=""):
            return "http://localhost"  # без порта

    monkeypatch.setattr(of, "EnvironmentVariables", lambda: V(), raising=True)
    with pytest.raises(ValueError):
        of.OAuthFlow.get_port()
