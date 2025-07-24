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
import os
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
from SRC.GENERAL.constant import Constant as C
from SRC.GENERAL.textmessage import TextMessage as T
from SRC.YADISK.exceptions import AuthError, AuthCancelledError, RefreshTokenError
from SRC.SECURITY.generate_pkce_pair import generate_pkce_params
from SRC.SECURITY.is_valid_redirect_uri import is_valid_redirect_uri

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
            raise RuntimeError(T.error_processing_request.format(e=e)) from e

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
            html: str = C.HTML_WINDOW_SUCCESSFUL
            self.wfile.write(html.encode(C.ENCODING))
        else:
            self.send_response(204)
            self.end_headers()


class TokenManager:
    """Управляет жизненным циклом OAuth-токенов для Яндекс-Диска.

    Отвечает за:
    - Сохранение и загрузку токенов из secure storage (keyring)
    - Проверку валидности и срока действия токенов
    - Взаимодействие с API Яндекс-Диска для проверки токенов

    Attributes:
        variables (EnvironmentVariables): Обертка для работы с переменными окружения и keyring
    """

    def __init__(self, env_vars: EnvironmentVariables) -> None:
        self.variables = env_vars

    def save_tokens(
        self, access_token: str, refresh_token: str | None, expires_at: str
    ) -> None:
        """Сохраняет токены и время жизни токена в secure storage.

        Args:
            access_token (str): Токен для API-запросов
            refresh_token (str): Токен для обновления access token
            expires_at (str): Время окончания действия токена для API-запросов

        Note:
            Автоматически вычитает 60 секунд из expires_in для раннего обновления
        """
        try:
            # Сохраняем токены и время истечения в памяти (keyring)
            self.variables.put_keyring_var(C.ACCESS_TOKEN, access_token)
            self.variables.put_keyring_var(C.EXPIRES_AT, expires_at)
            if refresh_token:
                self.variables.put_keyring_var(C.REFRESH_TOKEN, refresh_token)

            logger.debug(T.tokens_saved)

        except Exception as e:
            raise AuthError(T.error_saving_tokens.format(e=e)) from e

    def get_vars(self) -> tuple[str, str, str] | None:
        access_token = self.variables.get_var(C.ACCESS_TOKEN)
        refresh_token = self.variables.get_var(C.REFRESH_TOKEN)
        expires_at = self.variables.get_var(C.EXPIRES_AT)

        logger.debug(
            f"[Token Load] {C.ACCESS_TOKEN}: {C.PRESENT if access_token else C.MISSING}"
        )
        logger.debug(
            f"[Token Load] {C.REFRESH_TOKEN}: {C.PRESENT if refresh_token else C.MISSING}"
        )
        logger.debug(
            f"[Token Load] {C.EXPIRES_AT}: {C.PRESENT if expires_at else C.MISSING}"
        )

        return access_token, refresh_token, expires_at

    @staticmethod
    def _valid_expires_at(expires_at: str) -> bool:
        try:
            expires_at_float = float(expires_at)
        except (TypeError, ValueError) as e:
            logger.warning(T.not_float.format(e=e))
            return False

        current_time = time.time()
        if current_time >= expires_at_float:
            seconds = f"{current_time - expires_at_float:.0f}"
            logger.info(T.token_expired.format(seconds=seconds))
            return False

        return True

    def load_and_validate_exist_tokens(self) -> dict[str, str] | None:
        """Загружает и проверяет токены из keyring"""
        try:
            _vars = self.get_vars()

            if _vars is None:
                return None

            access_token, refresh_token, expires_at = _vars

            if not all([access_token, expires_at]):
                return None

            if not self._valid_expires_at(expires_at):
                return None

            if not self._validate_token_api(access_token):
                return None

            logger.debug(T.valid_token_found.format(token=C.ACCESS_TOKEN))
            return {
                C.ACCESS_TOKEN: access_token,
                C.REFRESH_TOKEN: refresh_token,
                C.EXPIRES_AT: expires_at,
            }

        except Exception as e:
            logger.warning(T.error_load_tokens.format(e=e))
            return None

    @staticmethod
    def _validate_token_api(access_token: str) -> bool:
        """Проверяет валидность токена через API Яндекс-Диска"""
        try:
            response = requests.get(
                C.URL_API_YANDEX_DISK,
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=5,
            )

            if response.status_code == 200:
                logger.debug(T.token_valid)
                return True

            logger.warning(T.token_invalid.format(status=response.status_code))
            return False

        except requests.RequestException as e:
            logger.warning(T.error_check_token.format(e=e))
            return False


class OAuthFlow:
    """Реализует полный OAuth 2.0 flow с PKCE для Яндекс.Диска.

    Обрабатывает все этапы авторизации:
    1. Генерация PKCE параметров (code_verifier, code_challenge)
    2. Запуск локального сервера для callback
    3. Открытие браузера для авторизации
    4. Обмен кода на токены

    Attributes:
        token_manager (TokenManager): Менеджер для работы с токенами
        port (int): Порт для локального callback-сервера
        callback_received (bool): Флаг получения callback
        callback_path (str): URL callback с кодом авторизации
        refresh_token (str): Текущий refresh token
        access_token (str): Текущий access token
        _token_expires_at (float): Время истечения токена (timestamp)
        variables (EnvironmentVariables): Обертка для переменных окружения
    """

    def __init__(
        self,
        token_manager: TokenManager,
        port: int,
        env_vars: EnvironmentVariables,
    ):
        self.token_manager = token_manager
        self.port = port
        self.callback_received: bool = False
        self.callback_path: str | None = None
        self.refresh_token: str | None = None
        self.access_token: str | None = None
        self._token_expires_at: float = 0
        self.variables = env_vars

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
            raise AuthCancelledError(T.canceled_authorization) from e
        except AuthError as e:
            raise AuthError(T.authorization_error.format(e=e)) from e

    def token_in_memory(self) -> str | None:
        if self.access_token and not self.is_token_expired():
            logger.debug(T.token_in_memory)
            return self.access_token
        return None

    def loaded_tokens(self) -> dict[str, str] | None:
        tokens = self.token_manager.load_and_validate_exist_tokens()
        if tokens:
            self.access_token = tokens[C.ACCESS_TOKEN]
            self.refresh_token = tokens.get(C.REFRESH_TOKEN)
            self._token_expires_at = float(tokens[C.EXPIRES_AT])
            logger.debug(T.loaded_token)
            return tokens

        return None

    def updated_tokens(self) -> dict[str, str] | None:
        logger.debug(T.start_update_tokens)
        try:
            if tokens := self.get_tokens_from_url():
                logger.debug(T.updated_tokens)

                self.access_token = tokens[ACCESS_TOKEN_IN_TOKEN]
                self.refresh_token = tokens.get(REFRESH_TOKEN_IN_TOKEN)
                token_expires_at = self.create_expires_at(tokens)
                self.token_manager.save_tokens(
                    self.access_token, self.refresh_token, token_expires_at
                )
                return tokens
            else:
                logger.warning(T.updated_tokens_error.format(e=""))
        except RefreshTokenError as e:
            logger.warning(T.updated_tokens_error.format(e=e))

        return None

    def is_token_expired(self) -> bool:
        """Проверяет, истек ли срок действия токена"""
        return time.time() >= self._token_expires_at

    def run_full_auth_flow(self) -> str:
        """Выполняет полный цикл OAuth 2.0 аутентификации"""
        logger.info(T.start_full_auth_flow)
        try:
            return self.full_auth_flow()
        except TimeoutError as e:
            raise AuthCancelledError(T.authorization_timeout.format(e=e)) from e
        except Exception as e:
            raise AuthError(T.authorization_error.format(e=e)) from e

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
        redirect_uri = self.variables.get_var(C.YANDEX_REDIRECT_URI, "")

        if not is_valid_redirect_uri(redirect_uri):
            raise ValueError(
                T.no_correct_redirect_uri.format(redirect_uri=redirect_uri)
            )

        client = WebApplicationClient(
            self.variables.get_var(C.ENV_YANDEX_CLIENT_ID, "")
        )

        return client.prepare_request_uri(
            self.variables.get_var(C.AUTH_URL, C.URL_AUTORIZATION_YANDEX_OAuth),
            redirect_uri=self.variables.get_var(C.YANDEX_REDIRECT_URI, ""),
            scope=self.variables.get_var(C.YANDEX_SCOPE, ""),
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

    def start_auth_server(self) -> OAuthHTTPServer:
        """Запускает сервер для обработки callback"""
        server = OAuthHTTPServer(("localhost", self.port), CallbackHandler, self)
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
                raise TimeoutError(T.callback_timeout)
            time.sleep(0.1)

    def parse_callback(self) -> str:
        """Извлекает код авторизации из callback"""
        if not self.callback_path:
            raise AuthError(T.no_callback_path)

        # if not is_valid_redirect_uri(self.callback_path):
        #     raise AuthError(T.not_safe_uri.format(callback_path=self.callback_path))

        query = urlparse(self.callback_path).query
        params = parse_qs(query)

        if "error" in params:
            error_code = params["error"][0]
            error_desc = params.get("error_description", ["Unknown error"])[0]
            raise AuthError(f"{error_code} - {error_desc}")

        auth_code = params.get("code", [""])[0]
        if not auth_code:
            raise AuthError(T.no_auth_code)
        return auth_code

    def get_tokens(self, auth_code: str, code_verifier: str) -> dict:
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.variables.get_var(C.ENV_YANDEX_CLIENT_ID, ""),
            "code_verifier": code_verifier,
            "redirect_uri": C.YANDEX_REDIRECT_URI,
        }

        response = requests.post(
            self.variables.get_var(C.TOKEN_URL, C.TOKEN_URL_DEFAULT),
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
            raise AuthError(T.no_token_in_response)

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
            "refresh_token": self.variables.get_var(C.REFRESH_TOKEN),
            "client_id": self.variables.get_var(C.ENV_YANDEX_CLIENT_ID),
            "client_secret": self.variables.get_var(C.ENV_CLIENT_SECRET),
        }

        response = requests.post(
            self.variables.get_var(C.TOKEN_URL, C.TOKEN_URL_DEFAULT),
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if response.status_code >= 400:
            logger.warning(
                T.error_refresh_token.format(status_code=response.status_code, e="")
            )
            return None

        return self.return_tokens(response)

    @staticmethod
    def return_tokens(response: requests.Response) -> dict:
        try:
            tokens = response.json()
        except ValueError as e:
            raise RefreshTokenError(
                T.not_valid_json.format(e=e, response=response.text[:200])
            )

        if not isinstance(tokens, dict):
            raise RefreshTokenError(
                T.dictionary_expected.format(type=type(tokens), response=response.text)
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
                logger.info(T.expires_in_error.format(key=expires_in_str))
        else:
            expires_in = float("inf")
            logger.info(T.no_expires_in)

        self._token_expires_at = time.time() + expires_in - 60.0

        return str(self._token_expires_at)


class YandexOAuth:
    """Фасадный класс для OAuth авторизации в Яндекс.Диск.

    Предоставляет упрощенный интерфейс для получения access token,
    инкапсулируя всю логику OAuth 2.0 с PKCE.

    Attributes:
        token_manager (TokenManager): Менеджер токенов
        flow (OAuthFlow): OAuth 2.0 flow processor
    """

    def __init__(
        self,
        port: int,
    ):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        env_vars = EnvironmentVariables()
        self.token_manager = TokenManager(env_vars)
        self.flow = OAuthFlow(self.token_manager, port, env_vars)

    def get_access_token(self) -> str | None:
        """Получает действительный access token"""
        try:
            token = self.flow.get_access_token()
            if token:
                logger.info(T.successful_access_token)
                return token
            else:
                raise AuthError(T.failed_access_token)
        except Exception as e:
            raise AuthError(T.critical_error.format(e=e)) from e
