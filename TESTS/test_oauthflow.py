import types, pytest
from SRC.YADISK.OAUTH import oauthflow as oflow
from SRC.YADISK.OAUTH.oauthflow import OAuthFlow
from SRC.YADISK.OAUTH.exceptions import AuthCancelledError, AuthError
from SRC.YADISK.yandexconst import YandexConstants as YC


class DummyVars:
    def __init__(self, vals=None):
        self.vals = vals or {}

    def get_var(self, k, default=""):
        return self.vals.get(k, default)


def _mk_flow(vals=None):
    f = OAuthFlow()
    f.variables = DummyVars(
        vals
        or {
            YC.YANDEX_REDIRECT_URI: "http://localhost:8080/cb",
            YC.ENV_YANDEX_CLIENT_ID: "client-id",
        }
    )
    return f


def test_token_in_memory_and_expiry(monkeypatch):
    f = _mk_flow()
    f.access_token = "tok"
    f._token_expires_at = 2000.0
    monkeypatch.setattr(oflow.time, "time", lambda: 1000.0, raising=True)
    assert f.token_in_memory() == "tok"
    # simulate expiry
    monkeypatch.setattr(oflow.time, "time", lambda: 3000.0, raising=True)
    assert f.token_in_memory() is None


def test_loaded_tokens_sets_state(monkeypatch):
    f = _mk_flow()
    f.token_manager = types.SimpleNamespace(
        load_and_validate_exist_tokens=lambda: {
            YC.YANDEX_ACCESS_TOKEN: "A",
            YC.YANDEX_REFRESH_TOKEN: "R",
            YC.YANDEX_EXPIRES_AT: "1234",
        }
    )
    tokens = f.loaded_tokens()
    assert tokens
    assert f.access_token == "A"
    assert f.refresh_token == "R"
    assert f._token_expires_at == 1234.0


def test_updated_tokens_saves_and_sets(monkeypatch):
    f = _mk_flow()
    # Tokens returned from browser callback URL
    f.get_tokens_from_url = lambda: {
        "access_token": "A2",
        "refresh_token": "R2",
        "expires_in": "60",
    }
    # Force create_expires_at deterministic
    f.create_expires_at = lambda _: "9999"
    saved = {}
    f.token_manager = types.SimpleNamespace(
        save_tokens=lambda acc, ref, exp: saved.update(acc=acc, ref=ref, exp=exp)
    )
    tokens = f.updated_tokens()
    assert tokens["access_token"] == "A2"
    assert saved == {"acc": "A2", "ref": "R2", "exp": "9999"}


def test_build_auth_url_valid(monkeypatch):
    f = _mk_flow()
    # Accept redirect uri
    monkeypatch.setattr(oflow, "is_valid_redirect_uri", lambda _: True, raising=True)

    # Fake OAuth client
    class DC:
        def __init__(self, *_):
            pass

        def prepare_request_uri(self, *a, **k):
            return "AUTH_URL"

    monkeypatch.setattr(oflow, "WebApplicationClient", DC, raising=True)
    url = f.build_auth_url("challenge")
    assert url == "AUTH_URL"


def test_build_auth_url_invalid_raises(monkeypatch):
    f = _mk_flow()
    monkeypatch.setattr(oflow, "is_valid_redirect_uri", lambda _: False, raising=True)
    with pytest.raises(ValueError):
        f.build_auth_url("challenge")


def test_run_full_auth_flow_wrapping(monkeypatch):
    f = _mk_flow()
    # Timeout path
    monkeypatch.setattr(
        OAuthFlow,
        "full_auth_flow",
        lambda self: (_ for _ in ()).throw(TimeoutError("t")),
        raising=True,
    )
    with pytest.raises(AuthCancelledError):
        f.run_full_auth_flow()
    # Generic error path
    monkeypatch.setattr(
        OAuthFlow,
        "full_auth_flow",
        lambda self: (_ for _ in ()).throw(RuntimeError("x")),
        raising=True,
    )
    with pytest.raises(AuthError):
        f.run_full_auth_flow()
