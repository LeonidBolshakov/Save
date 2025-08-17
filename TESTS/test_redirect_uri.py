
import pytest
from SRC.YADISK.OAUTH.is_valid_redirect_uri import is_valid_redirect_uri

def test_valid_localhost_http():
    assert is_valid_redirect_uri("http://localhost:8080/callback") is True

def test_path_with_double_slash_is_invalid():
    assert is_valid_redirect_uri("http://localhost:8080//callback") is False

def test_dangerous_symbols_raise():
    with pytest.raises(ValueError):
        is_valid_redirect_uri("http://localhost:8080/<cb>")

def test_too_long_is_invalid():
    uri = "http://localhost:8080/" + "a"*190
    assert is_valid_redirect_uri(uri) is False
