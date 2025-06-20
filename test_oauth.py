import pytest
import sys
import json
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

# Добавляем путь к исходному коду
sys.path.insert(0, str(Path(__file__).parent.parent))

from yandex_disk import (
    OAuthFlow,
    TokenManager,
    OAuthHTTPServer,
    CallbackHandler,
    validate_environment_vars,
    parse_arguments,
    create_oauth_flow,
    main,
)


# Фикстуры
@pytest.fixture
def tokens_file(tmp_path):
    return tmp_path / "tokens.json"


@pytest.fixture
def env_vars(monkeypatch):
    """Устанавливает необходимые переменные окружения для тестов"""
    monkeypatch.setenv("YANDEX_CLIENT_ID", "test_client")
    monkeypatch.setenv("YANDEX_REDIRECT_URI", "http://test")
    monkeypatch.setenv("YANDEX_SCOPE", "test_scope")
    monkeypatch.setenv("AUTH_URL", "https://test.auth")
    monkeypatch.setenv("TOKEN_URL", "https://test.token")


@pytest.fixture
def valid_tokens(tokens_file):
    """Создает файл с валидными токенами"""
    tokens = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": time.time() + 3600,  # Действителен 1 час
    }
    with open(tokens_file, "w") as f:
        json.dump(tokens, f)
    return tokens


@pytest.fixture
def expired_tokens(tokens_file):
    """Создает файл с истёкшими токенами"""
    tokens = {
        "access_token": "expired_access_token",
        "refresh_token": "test_refresh_token",
        "expires_at": time.time() - 3600,  # Истек 1 час назад
    }
    with open(tokens_file, "w") as f:
        json.dump(tokens, f)
    return tokens


# Тесты для TokenManager
class TestTokenManager:
    def test_save_and_load_valid_tokens(self, tokens_file):
        """Сохранение и загрузка действительных токенов"""
        tm = TokenManager(tokens_file)
        tm.save_tokens("test_access", "test_refresh", 3600)

        tokens = tm.load_tokens()
        assert tokens["access_token"] == "test_access"
        assert tokens["refresh_token"] == "test_refresh"
        assert tokens["expires_at"] > time.time()

    def test_load_missing_file(self, tokens_file):
        """Загрузка отсутствующего файла токенов"""
        tm = TokenManager(tokens_file)
        assert tm.load_tokens() is None

    def test_load_expired_tokens(self, tokens_file):
        """Загрузка истёкших токенов"""
        tm = TokenManager(tokens_file)
        tm.save_tokens("test_access", "test_refresh", -3600)
        assert tm.load_tokens() is None


# Тесты для OAuthFlow
class TestOAuthFlow:
    def test_generate_pkce_params(self):
        """Генерация PKCE параметров"""
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)
        verifier, challenge = flow.generate_pkce_params()
        assert len(verifier) >= 64
        assert len(challenge) == 43
        assert "=" not in challenge

    def test_build_auth_url(self, env_vars):
        """Построение URL для авторизации"""
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)
        auth_url = flow.build_auth_url("test_challenge")
        assert "client_id=test_client" in auth_url
        assert "redirect_uri=http%3A%2F%2Ftest" in auth_url
        assert "scope=test_scope" in auth_url
        assert "code_challenge=test_challenge" in auth_url

    def test_parse_valid_callback(self):
        """Парсинг валидного callback URL"""
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)
        flow.callback_path = "http://localhost?code=test_code&state=123"
        assert flow.parse_callback() == "test_code"

    def test_parse_callback_error(self):
        """Обработка callback с ошибкой"""
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)
        flow.callback_path = "http://localhost?error=access_denied"
        with pytest.raises(RuntimeError, match="access_denied"):
            flow.parse_callback()

    @patch("yandex_disk.requests.post")
    @patch("yandex_disk.requests.get")
    def test_exchange_token_success(self, mock_get, mock_post, env_vars, tokens_file):
        """Успешный обмен кода на токены"""
        # Настраиваем мок ответа для получения токена
        mock_response_post = MagicMock()
        mock_response_post.status_code = 200
        mock_response_post.json.return_value = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response_post

        # Настраиваем мок ответа для проверки токена
        mock_response_get = MagicMock()
        mock_response_get.status_code = 200
        mock_response_get.json.return_value = {"total_space": 10000000000}  # 10 GB
        mock_get.return_value = mock_response_get

        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345, False)
        access_token = flow.exchange_token("test_code", "test_verifier")

        assert access_token == "new_access"
        assert flow.access_token == "new_access"
        assert flow.refresh_token == "new_refresh"
        assert tokens_file.exists()

        # Проверяем вызовы API
        mock_post.assert_called_once()
        mock_get.assert_called_once_with(
            "https://cloud-api.yandex.net/v1/disk",
            headers={"Authorization": "OAuth new_access"},
            timeout=15,
        )

    @patch("yandex_disk.requests.post")
    @patch("yandex_disk.requests.get")
    def test_refresh_token_success(self, mock_get, mock_post, env_vars, tokens_file):
        """Успешное обновление токена"""
        # Настраиваем мок ответа для обновления токена
        mock_response_post = MagicMock()
        mock_response_post.status_code = 200
        mock_response_post.json.return_value = {
            "access_token": "refreshed_access",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response_post

        # Настраиваем мок ответа для проверки токена
        mock_response_get = MagicMock()
        mock_response_get.status_code = 200
        mock_response_get.json.return_value = {"total_space": 10000000000}
        mock_get.return_value = mock_response_get

        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345, False)
        flow.refresh_token = "old_refresh"
        access_token = flow.refresh_access_token()

        assert access_token == "refreshed_access"
        assert flow.refresh_token == "new_refresh"

        # Проверяем вызовы API
        mock_post.assert_called_once()
        mock_get.assert_called_once_with(
            "https://cloud-api.yandex.net/v1/disk",
            headers={"Authorization": "OAuth refreshed_access"},
            timeout=15,
        )

    @patch("yandex_disk.OAuthFlow.run_full_auth_flow")
    @patch("yandex_disk.TokenManager.load_tokens")
    def test_get_access_token_from_storage(
        self, mock_load, mock_auth, valid_tokens, tokens_file
    ):
        """Получение токена из хранилища"""
        mock_load.return_value = valid_tokens
        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345, False)
        token = flow.get_access_token()
        assert token == "test_access_token"
        mock_auth.assert_not_called()

    @patch("yandex_disk.OAuthFlow.refresh_access_token")
    @patch("yandex_disk.TokenManager.load_tokens")
    def test_get_access_token_refresh(
        self, mock_load, mock_refresh, expired_tokens, tokens_file
    ):
        """Обновление истёкшего токена"""
        mock_load.return_value = expired_tokens

        # Создаем объект flow
        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345, False)

        # Помечаем токен как истёкший
        flow.token_expired = True

        # Настраиваем мок для обновления токена
        mock_refresh.return_value = "refreshed_token"

        token = flow.get_access_token()
        assert token == "refreshed_token"
        mock_refresh.assert_called_once()

    @patch("yandex_disk.OAuthFlow.run_full_auth_flow")
    @patch("yandex_disk.TokenManager.load_tokens")
    def test_get_access_token_full_auth(self, mock_load, mock_auth, tokens_file):
        """Запуск полной аутентификации при отсутствии токенов"""
        mock_load.return_value = None
        mock_auth.return_value = "new_token"

        tm = TokenManager(tokens_file)
        flow = OAuthFlow(tm, 12345, False)
        token = flow.get_access_token()
        assert token == "new_token"
        mock_auth.assert_called_once()


# Тесты для CallbackHandler
# Тесты для CallbackHandler
class TestCallbackHandler:
    def test_valid_callback(self):
        """Обработка валидного callback запроса"""
        # Создаём МОК для сокета
        mock_socket = MagicMock()

        # Создаем объект OAuthFlow
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)

        # Создаем сервер
        server = OAuthHTTPServer(("localhost", 12345), CallbackHandler, flow)

        # Создаем обработчик
        handler = CallbackHandler(mock_socket, ("127.0.0.1", 54321), server)

        # Мокируем необходимые атрибуты экземпляра
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        # Имитируем запрос с параметрами
        handler.path = "/callback?code=test_code"
        handler.do_GET()

        # Проверяем установку состояния
        assert flow.callback_received is True
        assert flow.callback_path == "/callback?code=test_code"

        # Проверяем вызовы методов ответа
        handler.send_response.assert_called_once_with(200)
        handler.send_header.assert_called_with(
            "Content-type", "text/html; charset=utf-8"
        )
        handler.end_headers.assert_called_once()
        handler.wfile.write.assert_called_once()

    def test_invalid_callback(self):
        """Обработка запроса без параметров"""
        # Создаём МОК для сокета
        mock_socket = MagicMock()

        # Создаем объект OAuthFlow
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)

        # Создаем сервер
        server = OAuthHTTPServer(("localhost", 12345), CallbackHandler, flow)

        # Создаем обработчик
        handler = CallbackHandler(mock_socket, ("127.0.0.1", 54321), server)

        # Мокируем необходимые атрибуты экземпляра
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()

        # Имитируем запрос без параметров
        handler.path = "/favicon.ico"
        handler.do_GET()

        # Проверяем, что состояние не изменилось
        assert flow.callback_received is False
        assert flow.callback_path is None

        # Проверяем вызовы методов ответа
        handler.send_response.assert_called_once_with(204)
        handler.end_headers.assert_called_once()

    @patch.object(CallbackHandler, "send_response")
    @patch.object(CallbackHandler, "end_headers")
    def test_invalid_callback(self, mock_end_headers, mock_send_response):
        """Обработка запроса без параметров"""
        # Создаём МОК для сокета
        mock_socket = MagicMock()

        # Создаем объект OAuthFlow
        tm = TokenManager(Path("tokens.json"))
        flow = OAuthFlow(tm, 12345, False)

        # Создаем сервер
        server = OAuthHTTPServer(("localhost", 12345), CallbackHandler, flow)

        # Создаем обработчик
        handler = CallbackHandler(mock_socket, ("127.0.0.1", 54321), server)

        # Имитируем запрос без параметров
        handler.path = "/favicon.ico"
        handler.do_GET()

        # Проверяем, что состояние не изменилось
        assert flow.callback_received is False
        assert flow.callback_path is None

        # Проверяем вызовы методов ответа
        mock_send_response.assert_called_once_with(204)
        mock_end_headers.assert_called_once()


# Тесты для основной точки входа
@patch("yandex_disk.OAuthFlow")
@patch("sys.argv", [__file__])  # Фиксируем sys.argv
def test_main_success(MockOAuthFlow, monkeypatch, capsys):
    """Успешное выполнение основной программы"""
    monkeypatch.setenv("YANDEX_CLIENT_ID", "test_client")
    monkeypatch.setenv("YANDEX_REDIRECT_URI", "http://test")
    monkeypatch.setenv("YANDEX_SCOPE", "test_scope")

    mock_flow = MockOAuthFlow.return_value
    mock_flow.get_access_token.return_value = "final_token"

    main()

    captured = capsys.readouterr()
    assert captured.out.strip() == "final_token"


@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
@patch("yandex_disk.OAuthFlow")
@patch("sys.argv", [__file__])
def test_main_failure(MockOAuthFlow, monkeypatch, caplog):
    """Обработка ошибки в основной программе"""
    monkeypatch.setenv("YANDEX_CLIENT_ID", "test_client")
    monkeypatch.setenv("YANDEX_REDIRECT_URI", "http://test")
    monkeypatch.setenv("YANDEX_SCOPE", "test_scope")

    mock_flow = MockOAuthFlow.return_value
    mock_flow.get_access_token.side_effect = Exception("Test error")

    with pytest.raises(SystemExit):
        main()

    # Проверяем логи через caplog вместо capsys
    assert any(
        record.levelname == "CRITICAL" and "Test error" in record.message
        for record in caplog.records
    )


def test_validate_environment_vars_success(monkeypatch):
    """Проверка успешной валидации переменных окружения"""
    monkeypatch.setenv("YANDEX_CLIENT_ID", "test")
    monkeypatch.setenv("YANDEX_REDIRECT_URI", "http://test")
    monkeypatch.setenv("YANDEX_SCOPE", "test_scope")
    validate_environment_vars()  # Не должно быть исключений


def test_validate_environment_vars_failure(monkeypatch):
    """Проверка отсутствия обязательных переменных"""
    monkeypatch.delenv("YANDEX_CLIENT_ID", raising=False)
    with pytest.raises(EnvironmentError):
        validate_environment_vars()


def test_create_oauth_flow():
    """Тестирование фабрики создания OAuthFlow"""
    args = MagicMock()
    args.tokens_file = "test_tokens.json"
    args.port = 54321
    args.no_browser = True

    flow = create_oauth_flow(args)
    assert flow.token_manager.tokens_file == Path("test_tokens.json")
    assert flow.port == 54321
    assert flow.open_browser_flag is False


def test_parse_arguments():
    """Тестирование парсинга аргументов командной строки"""
    # Сохраняем оригинальные аргументы
    original_argv = sys.argv

    try:
        # Устанавливаем тестовые аргументы
        sys.argv = [__file__, "--tokens-file=test.json", "--port=9999", "--no-browser"]

        args = parse_arguments()
        # noinspection PyTestUnpassedFixture
        assert args.tokens_file == "test.json"
        assert args.port == 9999
        assert args.no_browser is True
    finally:
        # Восстанавливаем оригинальные аргументы
        sys.argv = original_argv
