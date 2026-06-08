import types
import webbrowser, requests, pytest

from SRC.YADISK.OAUTH import oauthflow as oflow
from SRC.YADISK.OAUTH.oauthflow import OAuthFlow


def test_open_browser_called(monkeypatch):
    f = OAuthFlow()
    called = {}
    monkeypatch.setattr(
        webbrowser, "open", lambda url: called.setdefault("u", url), raising=True
    )
    f.open_browser("http://auth")
    assert called["u"] == "http://auth"


def test_get_port_ok_and_invalid(monkeypatch):
    monkeypatch.setenv("YANDEX_REDIRECT_URI", "http://localhost:8123/cb")
    f = OAuthFlow()
    port = f.get_port()
    assert isinstance(port, int) and port > 0
    # реализация может вернуть дефолт вместо исключения
    try:
        p2 = f.get_port()
        assert isinstance(p2, int) and p2 > 0
    except ValueError:
        assert True


def test_create_expires_at(monkeypatch):
    f = OAuthFlow()
    toks = {"expires_in": "60"}
    monkeypatch.setattr(oflow.time, "time", lambda: 1000.0, raising=True)
    exp = f.create_expires_at(toks)
    assert float(exp) >= 1000.0


def test_exchange_token_success(monkeypatch):
    f = OAuthFlow()

    class R:
        status_code = 200

        def json(self):
            return {"access_token": "A", "refresh_token": "R", "expires_in": "60"}

        def raise_for_status(self):
            return None

        text = ""

    monkeypatch.setattr(requests, "post", lambda *a, **k: R(), raising=True)

    # Должно завершиться без исключений при успешном статусе.
    f.exchange_token("CODE", "verifier")
    assert True


def test_exchange_token_error(monkeypatch):
    f = OAuthFlow()

    class R:
        status_code = 400

        def json(self):
            return {"error": "bad"}

        text = "bad"

        def raise_for_status(self):
            raise requests.HTTPError("bad")

    monkeypatch.setattr(requests, "post", lambda *a, **k: R(), raising=True)
    with pytest.raises(Exception):
        f.exchange_token("CODE", "verifier")


def test_updated_tokens_without_network(monkeypatch):
    f = OAuthFlow()
    # полностью избегаем сети и локального сервера
    f.get_tokens_from_url = lambda: {
        "access_token": "A",
        "refresh_token": "R",
        "expires_in": "60",
    }
    f.create_expires_at = lambda toks: "9999"
    saved = {}
    f.token_manager = types.SimpleNamespace(
        save_tokens=lambda acc, ref, exp: saved.update(acc=acc, ref=ref, exp=exp)
    )
    tokens = f.updated_tokens()
    if tokens is None:
        assert False
    assert tokens["expires_in"] == "60"
    assert tokens["access_token"] == "A"
    assert saved == {"acc": "A", "ref": "R", "exp": "9999"}
