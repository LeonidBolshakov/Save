import types, pytest
from SRC.YADISK.OAUTH.oauthflow import OAuthFlow
import SRC.YADISK.OAUTH.oauthflow as oflow


def _mk(valid_uri=True):
    f = OAuthFlow()
    # force redirect uri validity
    if valid_uri:
        f.redirect_uri = "http://localhost:8123/cb"
    else:
        f.redirect_uri = "http://example.com#frag"  # invalid
    # provide client id
    f.yandex_client_id = "cid"
    # stub token_manager but not used here
    f.token_manager = types.SimpleNamespace(save_tokens=lambda *a, **k: None)
    return f


def test_build_auth_url_ok():
    f = _mk(True)
    url = f.build_auth_url("challenge")
    assert (
        "response_type=code" in url
        and "code_challenge=challenge" in url
        and "client_id=cid" in url
    )


def test_build_auth_url_invalid():
    f = _mk(False)
    with pytest.raises(ValueError):
        f.build_auth_url("challenge")


def test_get_tokens_from_url_status_400(monkeypatch):
    f = _mk(True)
    # variables to provide refresh token and secret
    f.variables = types.SimpleNamespace(get_var=lambda k, default="": "x")

    class R:
        status_code = 400
        text = "bad"

    monkeypatch.setattr(oflow.requests, "post", lambda *a, **k: R(), raising=True)
    assert f.get_tokens_from_url() is None


def test_create_expires_at_without_key(monkeypatch):
    f = _mk(True)
    monkeypatch.setattr(oflow.time, "time", lambda: 1000.0, raising=True)
    s = f.create_expires_at({})  # no 'expires_in'
    assert s.lower() == "inf"
