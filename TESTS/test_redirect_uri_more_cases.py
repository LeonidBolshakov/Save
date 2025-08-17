
import pytest
from SRC.YADISK.OAUTH.is_valid_redirect_uri import is_valid_redirect_uri

def test_valid_localhost_http():
    assert is_valid_redirect_uri("http://localhost:8123/cb")

def test_valid_https_domain():
    assert is_valid_redirect_uri("https://example.com/callback")

def test_invalid_domain_and_port_and_fragment():
    assert is_valid_redirect_uri("") is False
    assert is_valid_redirect_uri("http://bad_domain/cb") is False
    try:
        ok = is_valid_redirect_uri("http://example.com:70000/cb")
        assert ok is False
    except ValueError:
        assert True
    try:
        ok = is_valid_redirect_uri("http://example.com/cb#frag")
        assert ok is False
    except ValueError:
        assert True

def test_double_slash_in_path_is_invalid():
    assert is_valid_redirect_uri("http://example.com/cb//next") is False

def test_dangerous_symbols_raise():
    with pytest.raises(ValueError):
        is_valid_redirect_uri("http://example.com/<cb>")

def test_too_long_is_invalid():
    long_uri = "http://example.com/" + ("a"*201)
    assert is_valid_redirect_uri(long_uri) is False
