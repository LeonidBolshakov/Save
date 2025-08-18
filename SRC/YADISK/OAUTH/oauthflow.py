"""
Модуль для OAuth 2.0 авторизации в Яндекс-Диск.
Реализует получение, обновление и валидацию токенов доступа
с поддержкой PKCE для безопасной авторизации.

Основные компоненты:
- YandexOAuth: Фасад для управления процессом авторизации
- OAuthFlow: Управление OAuth 2.0 потоком
- TokenManager: Работа с токенами (сохранение/загрузка)
- OAuthHTTPServer: HTTP-сервер для обработки callback
"""

from __future__ import annotations
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import time
import threading
import requests
from urllib.parse import urlparse, parse_qs
from typing import Any, cast
import logging

logger = logging.getLogger(__name__)

from oauthlib.oauth2 import WebApplicationClient

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.YADISK.OAUTH.exceptions import AuthError, AuthCancelledError, RefreshTokenError
from SRC.YADISK.OAUTH.generate_pkce_pair import generate_pkce_params
from SRC.YADISK.OAUTH.is_valid_redirect_uri import is_valid_redirect_uri
from SRC.YADISK.OAUTH.tokenmanager import TokenManager
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT
from SRC.GENERAL.constants import Constants as C
from SRC.YADISK.yandexconst import YandexConstants as YC

ACCESS_TOKEN_IN_TOKEN = "access_token"
REFRESH_TOKEN_IN_TOKEN = "refresh_token"
EXPIRES_IN_IN_TOKEN = "expires_in"


class OAuthHTTPServer(HTTPServer):
    """Кастомный HTTP-сервер для OAuth-авторизации"""

    def __init__(
            self, server_address: tuple[str, int], handler_class: Any, oauth_flow: OAuthFlow
    ) -> None:
        super().__init__(server_address, handler_class)
        self.oauth_flow: OAuthFlow = oauth_flow


class CallbackHandler(BaseHTTPRequestHandler):
    """Обработчик callback-запросов от OAuth-провайдера"""

    def handle(self) -> None:
        try:
            super().handle()
        except Exception as e:
            raise RuntimeError(YT.error_processing_request.format(e=e))

    def log_message(self, format_: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        server: OAuthHTTPServer = cast(OAuthHTTPServer, self.server)
        state: OAuthFlow = server.oauth_flow

        if "?" in self.path:
            state.callback_path = self.path
            state.callback_received = True

            threading.Thread(target=server.shutdown, daemon=True).start()

            self.send_response(200)
            self.send_header("Content-type", f"text/html; charset={C.ENCODING}")
            self.end_headers()
            html: str = YC.YANDEX_HTML_WINDOW_SUCCESSFUL
            self.wfile.write(html.encode(C.ENCODING))
        else:
            self.send_response(204)
            self.end_headers()


class OAuthFlow:
    """Реализует полный OAuth 2.0 flow с PKCE для Яндекс.Диска.

    Обрабатывает все этапы авторизации:
    1. Генерация PKCE параметров (code_verifier, code_challenge)
    2. Запуск локального сервера для callback
    3. Открытие браузера для авторизации
    4. Обмен кода на токены

    Attributes:
        token_manager (TokenManager): Менеджер для работы с токенами
        callback_received (bool): Флаг получения callback
        callback_path (str): URL callback с кодом авторизации
        refresh_token (str): Текущий refresh token
        access_token (str): Текущий access token
        _token_expires_at (float): Время истечения токена (timestamp)
        variables (EnvironmentVariables): Обертка для переменных окружения
    """

    def __init__(self) -> None:
        self.token_manager = TokenManager()
        self.callback_received: bool = False
        self.callback_path: str | None = None
        self.refresh_token: str | None = None
        self.access_token: str | None = None
        self._token_expires_at: float = 0
        self.variables = EnvironmentVariables()
        self.redirect_uri = self.variables.get_var(YC.YANDEX_REDIRECT_URI, "")
        self.yandex_client_id = self.variables.get_var(YC.ENV_YANDEX_CLIENT_ID, "")

    def get_access_token(self) -> str | None:
        """Получает действительный access token"""
        try:
            # 1. Проверка токена в памяти
            token = self.token_in_memory()
            if token:
                return self.access_token
            self.access_token = None

            # 2. Попытка загрузить сохраненные токены из хранилища компьютера (keyring)
            tokens = self.loaded_tokens()
            if tokens:
                return self.access_token
            self.access_token = None

            # 3. Попытка обновить токен
            tokens = self.updated_tokens()
            if tokens:
                return self.access_token
            self.access_token = None

            # 4. Полная аутентификация
            return self.run_full_auth_flow()

        except AuthCancelledError as e:
            raise AuthCancelledError(YT.canceled_authorization)
        except AuthError as e:
            raise AuthError(YT.authorization_error.format(e=e))

    def token_in_memory(self) -> str | None:
        if self.access_token and not self.is_token_expired():
            logger.debug(YT.token_in_memory)
            return self.access_token
        return None

    def loaded_tokens(self) -> dict[str, str] | None:
        tokens = self.token_manager.load_and_validate_exist_tokens()
        if tokens:
            self.access_token = tokens[YC.YANDEX_ACCESS_TOKEN]
            self.refresh_token = tokens.get(YC.YANDEX_REFRESH_TOKEN)
            self._token_expires_at = float(tokens[YC.YANDEX_EXPIRES_AT])
            logger.debug(YT.loaded_token)
            return tokens

        return None

    def updated_tokens(self) -> dict[str, str] | None:
        logger.debug(YT.start_update_tokens)
        try:
            if tokens := self.get_tokens_from_url():
                logger.debug(YT.updated_tokens)

                self.access_token = tokens[ACCESS_TOKEN_IN_TOKEN]
                self.refresh_token = tokens.get(REFRESH_TOKEN_IN_TOKEN)
                token_expires_at = self.create_expires_at(tokens)
                self.token_manager.save_tokens(
                    self.access_token, self.refresh_token, token_expires_at
                )
                return tokens
            else:
                logger.warning(YT.updated_tokens_error.format(e=""))
        except RefreshTokenError as e:
            logger.warning(YT.updated_tokens_error.format(e=e))

        return None

    def is_token_expired(self) -> bool:
        """Проверяет, истек ли срок действия токена"""
        return time.time() >= self._token_expires_at

    def run_full_auth_flow(self) -> str:
        """Выполняет полный цикл OAuth 2.0 аутентификации"""
        logger.info(YT.start_full_auth_flow)
        try:
            return self.full_auth_flow()
        except TimeoutError as e:
            raise AuthCancelledError(YT.authorization_timeout.format(e=e))
        except Exception as e:
            raise AuthError(YT.authorization_error.format(e=e))

    def full_auth_flow(self) -> str:
        """Содержательная часть метода start_full_auth_flow"""
        code_verifier, code_challenge = generate_pkce_params()
        auth_url = self.build_auth_url(code_challenge)
        self.start_auth_server()

        self.open_browser(auth_url)
        self.wait_for_callback()

        auth_code = self.parse_callback()
        token = self.exchange_token(auth_code, code_verifier)

        return token

    def build_auth_url(self, code_challenge: str) -> str:
        """Строит URL для авторизации с валидацией redirect_uri."""
        if not is_valid_redirect_uri(self.redirect_uri):
            raise ValueError(
                YT.no_correct_redirect_uri.format(redirect_uri=self.redirect_uri)
            )

        client = WebApplicationClient(self.yandex_client_id)

        return client.prepare_request_uri(
            YC.URL_AUTORIZATION_YANDEX_OAuth,
            redirect_uri=self.redirect_uri,
            scope=YC.YANDEX_SCOPE,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

    def start_auth_server(self) -> OAuthHTTPServer:
        """Запускает сервер для обработки callback"""
        server = OAuthHTTPServer(("localhost", self.get_port()), CallbackHandler, self)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return server

    @staticmethod
    def open_browser(auth_url: str) -> None:
        """Открывает браузер для авторизации"""
        webbrowser.open(auth_url)

    def wait_for_callback(self) -> None:
        """Ожидает callback от OAuth провайдера"""
        start_time = time.time()
        while not self.callback_received:
            if time.time() - start_time > 120:
                raise TimeoutError(YT.callback_timeout)
            time.sleep(0.1)

    def parse_callback(self) -> str:
        """Извлекает код авторизации из callback"""
        if not self.callback_path:
            raise AuthError(YT.no_callback_path)

        query = urlparse(self.callback_path).query
        params = parse_qs(query)

        if "error" in params:
            error_code = params["error"][0]
            error_desc = params.get("error_description", ["Unknown error"])[0]
            raise AuthError(f"{error_code} - {error_desc}")

        auth_code = params.get("code", [""])[0]
        if not auth_code:
            raise AuthError(YT.no_auth_code)
        return auth_code

    def get_tokens(self, auth_code: str, code_verifier: str) -> dict:
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.yandex_client_id,
            "code_verifier": code_verifier,
            "redirect_uri": self.redirect_uri,
        }

        response = requests.post(
            YC.YANDEX_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        return self.return_tokens(response)

    def exchange_token(self, auth_code: str, code_verifier: str) -> str:
        """Выполняет обмен authorization code на токены доступа.

        Args:
            auth_code (str): Код авторизации из callback
            code_verifier (str): PKCE code_verifier для проверки

        Returns:
            str: Полученный access token

        Raises:
            AuthError: При ошибках обмена токенов
        """

        token = self.get_tokens(auth_code, code_verifier)
        if ACCESS_TOKEN_IN_TOKEN not in token:
            raise AuthError(YT.no_token_in_response)

        self.access_token = token[ACCESS_TOKEN_IN_TOKEN]
        self.refresh_token = token.get(REFRESH_TOKEN_IN_TOKEN, self.refresh_token)

        # Время истечения токена(expires_at)
        expires_at = self.create_expires_at(token)

        self.token_manager.save_tokens(
            self.access_token, self.refresh_token or "", expires_at
        )
        return self.access_token

    def get_tokens_from_url(self) -> dict | None:
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.variables.get_var(YC.YANDEX_REFRESH_TOKEN),
            "client_id": self.yandex_client_id,
            "client_secret": self.variables.get_var(YC.ENV_YANDEX_CLIENT_SECRET),
        }
        print(
            f"{self.variables.get_var(YC.YANDEX_REFRESH_TOKEN)=}\n"
            f"{self.yandex_client_id=}\n"
            f"{self.variables.get_var(YC.ENV_YANDEX_CLIENT_SECRET)=}"
        )
        input("*****")

        response = requests.post(
            YC.YANDEX_TOKEN_URL,
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if response.status_code >= 400:
            logger.warning(
                YT.error_refresh_token.format(status_code=response.status_code)
            )
            return None

        return self.return_tokens(response)

    @staticmethod
    def return_tokens(response: requests.Response) -> dict:
        try:
            tokens = response.json()
        except ValueError as e:
            raise RefreshTokenError(
                YT.not_valid_json.format(e=e, response=response.text[:200])
            )

        if not isinstance(tokens, dict):
            raise RefreshTokenError(
                YT.dictionary_expected.format(
                    type=type(tokens), response=response.text[:200]
                )
            )

        return tokens

    def create_expires_at(self, tokens) -> str:
        """
        Добывает  expires_in из токена
        :param tokens:
        :return:
        """
        if EXPIRES_IN_IN_TOKEN in tokens:
            expires_in_str = tokens[EXPIRES_IN_IN_TOKEN]
            try:
                expires_in = float(expires_in_str)
            except ValueError:
                expires_in = 0.0
                logger.info(YT.expires_in_error.format(key=expires_in_str))
        else:
            expires_in = float("inf")
            logger.info(YT.no_expires_in)

        self._token_expires_at = time.time() + expires_in - 60.0

        return str(self._token_expires_at)

    @staticmethod
    def get_port() -> int:
        variables = EnvironmentVariables()
        try:
            uri = variables.get_var(YC.YANDEX_REDIRECT_URI)
            parsed = urlparse(uri)
            if parsed.port is None or parsed.port == "":
                raise ValueError(YT.invalid_port.format(e=""))
            return parsed.port
        except ValueError as e:
            raise ValueError(YT.invalid_port.format(e=e)) from e
