
from SRC.YADISK.OAUTH.yandexoauth import YandexOAuth, AuthError

def test_get_access_token_success(monkeypatch):
    yo = YandexOAuth()
    # In TESTING=1 it should use internal _Flow and return TEST_TOKEN
    assert yo.get_access_token() == "TEST_TOKEN"

def test_get_access_token_error(monkeypatch):
    yo = YandexOAuth()
    class BadFlow:
        def get_access_token(self): raise RuntimeError("fail")
    yo.flow = BadFlow()
    import pytest
    with pytest.raises(AuthError):
        yo.get_access_token()
