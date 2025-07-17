import pytest
import time
import requests
from unittest.mock import patch, mock_open
from SRC.yandex_token import (
    YandexOAuth,
    OAuthFlow,
    TokenManager,
    AuthCancelledError,
    RefreshTokenError,
    parse_arguments,
    main,
)


# Фикстура для временного файла токенов
@pytest.fixture
def tokens_file(tmp_path):
    return tmp_path / "tokens.json"


# Фикстура для мока переменных окружения
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("YANDEX_CLIENT_ID", "test_client")
    monkeypatch.setenv("YANDEX_REDIRECT_URI", "http://localhost")
    monkeypatch.setenv("YANDEX_SCOPE", "test_scope")
    monkeypatch.setenv("OAUTHLIB_INSECURE_TRANSPORT", "1")


# Тесты
class TestYandexOAuth:
    """Тесты для класса YandexOAuth"""

    def test_initialization(self, tokens_file):
        auth = YandexOAuth(tokens_file=str(tokens_file), port=12345)
        assert auth.token_manager.tokens_file == tokens_file
        assert auth.flow.port == 12345

    @patch("SRC.yandex_token.OAuthFlow.get_access_token")
    def test_get_token_success(self, mock_get_token, tokens_file):
        mock_get_token.return_value = "test_token"
        auth = YandexOAuth(tokens_file=str(tokens_file), port=12345)
        assert auth.get_token() == "test_token"

    @patch("SRC.yandex_token.OAuthFlow.get_access_token")
    def test_get_token_failure(self, mock_get_token, tokens_file):
        mock_get_token.return_value = None
        auth = YandexOAuth(tokens_file=str(tokens_file), port=12345)
        assert auth.get_token() is None

    @patch("SRC.yandex_token.OAuthFlow.refresh_access_token")
    def test_refresh_token_success(self, mock_refresh, tokens_file):
        mock_refresh.return_value = "refreshed_token"
        auth = YandexOAuth(tokens_file=str(tokens_file), port=12345)
        auth.flow.refresh_token = "valid_refresh_token"
        assert auth.refresh_token() == "refreshed_token"

    @patch("SRC.yandex_token.OAuthFlow.refresh_access_token")
    def test_refresh_token_failure(self, mock_refresh, tokens_file):
        mock_refresh.side_effect = RefreshTokenError("Test error")
        auth = YandexOAuth(tokens_file=str(tokens_file), port=12345)
        assert auth.refresh_token() is None


class TestTokenManager:
    """Тесты для класса TokenManager"""

    def test_save_and_load_tokens(self, tokens_file):
        tm = TokenManager(tokens_file)
        tm.save_tokens("access", "refresh", 3600)
        tokens = tm.load_valid_tokens()
        assert tokens["access_token"] == "access"
        assert tokens["refresh_token"] == "refresh"
        assert tokens["expires_at"] > time.time()

    def test_load_expired_tokens(self, tokens_file):
        tm = TokenManager(tokens_file)
        tm.save_tokens("access", "refresh", -3600)
        assert tm.load_valid_tokens() is None

    def test_load_invalid_file(self, tokens_file):
        tokens_file.write_text("{invalid json}")
        tm = TokenManager(tokens_file)
        assert tm.load_valid_tokens() is None

    @patch("requests.get")
    def test_validate_token_api_valid(self, mock_get, tokens_file):
        mock_get.return_value.status_code = 200
        tm = TokenManager(tokens_file)
        assert tm.validate_token_api("test_token") is True

    @patch("requests.get")
    def test_validate_token_api_invalid(self, mock_get, tokens_file):
        mock_get.return_value.status_code = 401
        tm = TokenManager(tokens_file)
        assert tm.validate_token_api("test_token") is False


class TestOAuthFlow:
    """Тесты для класса OAuthFlow"""

    @patch("SRC.yandex_token.OAuthFlow.run_full_auth_flow")
    def test_get_access_token_full_flow(self, mock_full_auth, tokens_file):
        mock_full_auth.return_value = "full_auth_token"
        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345)
        assert flow.get_access_token() == "full_auth_token"

    @patch("SRC.yandex_token.OAuthFlow.refresh_access_token")
    def test_get_access_token_refresh(self, mock_refresh, tokens_file):
        mock_refresh.return_value = "refreshed_token"
        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345)
        flow.refresh_token = "valid_refresh_token"
        flow._token_expires_at = time.time() - 100
        assert flow.get_access_token() == "refreshed_token"

    @patch("requests.post")
    def test_refresh_access_token_success(self, mock_post, tokens_file):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345)
        flow.refresh_token = "old_refresh"
        token = flow.refresh_access_token()

        assert token == "new_access"
        assert flow.access_token == "new_access"
        assert flow.refresh_token == "new_refresh"

    @patch("requests.post")
    def test_refresh_access_token_failure(self, mock_post, tokens_file):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = requests.HTTPError("400 Error")
        mock_post.return_value = mock_response

        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345)
        flow.refresh_token = "old_refresh"

        with pytest.raises(RefreshTokenError) as exc_info:
            flow.refresh_access_token()

        assert "400" in str(exc_info.value)


# test_yandex_token.py
import pytest
import sys
from unittest.mock import patch, MagicMock


def test_main_success(monkeypatch):
    # Подменяем parse_arguments, чтобы не использовать argparse
    monkeypatch.setattr(
        "SRC.yandex_token.parse_arguments",
        lambda: MagicMock(tokens_file="test_tokens.json", port=12345),
    )

    # Подменяем методы YandexOAuth
    mock_auth = MagicMock()
    mock_auth.get_token.return_value = "dummy_token"

    # Подменяем конструктор YandexOAuth, чтобы возвращал наш мок
    monkeypatch.setattr(
        "SRC.yandex_token.YandexOAuth", lambda tokens_file, port: mock_auth
    )

    # Подменяем sys.exit, чтобы не завершать тест
    with patch.object(sys, "exit") as mock_exit:
        main()
        mock_exit.assert_called_once_with(0)  # Успешное завершение


@pytest.mark.main
def test_parse_arguments():
    with patch(
        "sys.argv", [__file__, "--tokens-file", "custom.json", "--port", "54321"]
    ):
        args = parse_arguments()
        # noinspection PyTestUnpassedFixture
        assert args.tokens_file == "custom.json"
        assert args.port == 54321


# Тесты для крайних случаев
def test_auth_cancelled_error():
    with pytest.raises(AuthCancelledError):
        raise AuthCancelledError("Test")


def test_refresh_token_error():
    with pytest.raises(RefreshTokenError):
        raise RefreshTokenError("Test")


@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_token_manager_save(mock_json_dump, mock_file, tokens_file):
    tm = TokenManager(tokens_file)
    tm.save_tokens("access", "refresh", 3600)
    mock_file.assert_called_once_with(tokens_file, "w", encoding="utf-8")
    mock_json_dump.assert_called_once()
