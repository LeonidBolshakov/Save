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
import secrets
import base64
import hashlib
import time
import threading
import requests
from urllib.parse import urlparse, parse_qs
from oauthlib.oauth2 import WebApplicationClient
from typing import Any, cast
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constant import Constant as C

ACCESS_TOKEN_IN_TOKEN = "access_token"
REFRESH_TOKEN_IN_TOKEN = "refresh token"


class AuthError(Exception):
    """Базовое исключение для ошибок авторизации"""


class AuthCancelledError(AuthError):
    """Исключение при отмене авторизации пользователем"""


class RefreshTokenError(AuthError):
    """Ошибка при обновлении токена"""


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
            logger.error(f"Ошибка обработки запроса: {e}")
            raise RuntimeError(f"Ошибка обработки запроса: {e}") from None

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
    """Управляет сохранением и загрузкой токенов авторизации через keyring"""

    def __init__(self, env_vars: EnvironmentVariables) -> None:
        self.variables = env_vars

    def save_tokens(
        self, access_token: str, refresh_token: str, expires_in: float
    ) -> None:
        """Сохраняет токены в keyring"""
        try:
            # Сохраняем с временем истечения (expires_at)

            expires_at = time.time() + expires_in - 60

            self.variables.put_keyring_var(C.ACCESS_TOKEN, access_token)
            self.variables.put_keyring_var(C.REFRESH_TOKEN, refresh_token)
            self.variables.put_keyring_var("EXPIRES_AT", str(expires_at))

            logger.debug(
                f"Токены сохранены в keyring. Истекают: {time.ctime(expires_at)}"
            )

        except Exception as e:
            logger.error(f"Ошибка сохранения токенов в keyring: {e}")
            raise

    def get_vars(self) -> tuple[str, str, str] | None:
        access_token = self.variables.get_var(C.ACCESS_TOKEN)
        refresh_token = self.variables.get_var(C.REFRESH_TOKEN)
        expires_at = self.variables.get_var("EXPIRES_AT")

        logger.debug(
            f"[Token Load] {C.ACCESS_TOKEN}: {'present' if access_token else 'missing'}"
        )
        logger.debug(
            f"[Token Load] {C.REFRESH_TOKEN}: {'present' if refresh_token else 'missing'}"
        )
        logger.debug(
            f"[Token Load] EXPIRES_AT: {'present' if expires_at else 'missing'}"
        )

        return access_token, refresh_token, expires_at

    @staticmethod
    def _valid_expires_at(expires_at: str) -> bool:
        try:
            expires_at_float = float(expires_at)
        except (TypeError, ValueError) as e:
            logger.warning(
                f"[Token Load] Время истечения не число с плавающей запятой: {e}"
            )
            return False

        current_time = time.time()
        if current_time >= expires_at_float:
            logger.info(
                f"[Token Load] Токен истек {current_time - expires_at_float:.0f} сек назад"
            )
            return False

        return True

    def load_and_validate_exist_token(self) -> dict[str, str] | None:
        """Загружает и проверяет токены из keyring"""
        try:
            access_token, refresh_token, expires_at = self.get_vars()

            if not all([access_token, expires_at]):
                return None

            if not self._valid_expires_at(expires_at):
                return None

            if not self._validate_token_api(access_token):
                return None

            logger.debug(f"[Token Load] Найден валидный {C.ACCESS_TOKEN} в keyring")
            return {
                C.ACCESS_TOKEN: access_token,
                C.REFRESH_TOKEN: refresh_token,
                "expires_at": expires_at,
            }

        except Exception as e:
            logger.error(f"[Token Load] Ошибка загрузки токенов из keyring: {e}")
            return None

    @staticmethod
    def _validate_token_api(access_token: str) -> bool:
        """Проверяет валидность токена через API Яндекс-Диска"""
        try:
            response = requests.get(
                "https://cloud-api.yandex.net/v1/disk",
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=5,
            )

            if response.status_code == 200:
                logger.debug("Токен успешно прошел проверку через API")
                return True

            logger.debug(f"Токен недействителен. Код ответа: {response.status_code}")
            return False

        except requests.RequestException as e:
            logger.warning(f"Ошибка проверки токена через API: {e}")
            return False


class OAuthFlow:
    """Управляет процессом OAuth 2.0 авторизации"""

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
        self.token_state: str = "unknown"  # valid, expired, invalid
        self.variables = env_vars

    def get_access_token(self) -> str | None:
        """Получает действительный access token"""
        try:
            # 1. Проверка токена в памяти
            if (
                self.access_token
                and self.token_state == "valid"
                and not self.is_token_expired()
            ):
                logger.debug("Используется существующий валидный токен")
                return self.access_token

            # 2. Попытка загрузить сохраненные токены
            tokens = self.token_manager.load_and_validate_exist_token()
            if tokens:
                self.access_token = tokens[C.ACCESS_TOKEN]
                self.refresh_token = tokens.get(C.REFRESH_TOKEN)
                self._token_expires_at = float(tokens["expires_at"])
                self.token_state = "valid"
                logger.debug("Успешно загружены сохраненные токены")
                return self.access_token

            # 3. Попытка обновить токен
            if self.refresh_token:
                try:
                    if token := self.refresh_access_token():
                        logger.debug("Токен обновлён с помощью refresh_token")
                        return token
                except RefreshTokenError as e:
                    logger.warning(f"Не удалось обновить токен: {e}")
                    self.refresh_token = None
                    self.token_state = "invalid"

            # 4. Полная аутентификация
            logger.info("Запуск полного процесса аутентификации")
            return self.run_full_auth_flow()

        except AuthCancelledError:
            return None
        except AuthError as e:
            logger.error(f"Ошибка авторизации: {e}")
            return None

    def is_token_expired(self) -> bool:
        """Проверяет, истек ли срок действия токена"""
        return time.time() >= self._token_expires_at

    def run_full_auth_flow(self) -> str:
        """Выполняет полный цикл OAuth 2.0 аутентификации"""
        try:
            code_verifier, code_challenge = self.generate_pkce_params()
            auth_url = self.build_auth_url(code_challenge)
            self.start_auth_server()

            self.open_browser(auth_url)
            self.wait_for_callback()

            auth_code = self.parse_callback()
            token = self.exchange_token(auth_code, code_verifier)

            self.token_state = "valid"
            return token

        except TimeoutError as e:
            logger.error(f"Превышено время ожидания авторизации: {e}")
            raise AuthCancelledError("Превышено время ожидания авторизации") from e
        except Exception as e:
            logger.error(f"Ошибка в процессе авторизации: {e}")
            raise AuthError(f"Ошибка авторизации: {e}") from e

    @staticmethod
    def generate_pkce_params() -> tuple[str, str]:
        """Генерирует параметры PKCE"""
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .replace("=", "")
        )
        return code_verifier, code_challenge

    def build_auth_url(self, code_challenge: str) -> str:
        """Строит URL для авторизации"""
        client = WebApplicationClient(self.variables.get_var(C.YANDEX_CLIENT_ID, ""))
        return client.prepare_request_uri(
            self.variables.get_var(C.AUTH_URL, "https://oauth.yandex.ru/authorize"),
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
                raise TimeoutError("Таймаут ожидания callback")
            time.sleep(0.1)

    def parse_callback(self) -> str:
        """Извлекает код авторизации из callback"""
        if not self.callback_path:
            raise AuthError("Callback path не установлен")

        query = urlparse(self.callback_path).query
        params = parse_qs(query)

        if "error" in params:
            error_code = params["error"][0]
            error_desc = params.get("error_description", ["Unknown error"])[0]
            raise AuthError(f"{error_code} - {error_desc}")

        auth_code = params.get("code", [""])[0]
        if not auth_code:
            raise AuthError("Не удалось извлечь код авторизации")

        return auth_code

    def get_token(self, auth_code: str, code_verifier: str) -> dict:
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.variables.get_var(C.YANDEX_CLIENT_ID, ""),
            "code_verifier": code_verifier,
            "redirect_uri": self.variables.get_var(C.YANDEX_REDIRECT_URI, ""),
        }

        response = requests.post(
            self.variables.get_var("TOKEN_URL", "https://oauth.yandex.ru/token"),
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()

        return response.json()

    def exchange_token(self, auth_code: str, code_verifier: str) -> str:
        """Обменивает код авторизации на токены"""

        token = self.get_token(auth_code, code_verifier)
        if ACCESS_TOKEN_IN_TOKEN not in token:
            raise AuthError("Токен доступа не получен в ответе")

        self.access_token = token[ACCESS_TOKEN_IN_TOKEN]
        self.refresh_token = token.get(REFRESH_TOKEN_IN_TOKEN, self.refresh_token)

        if "expires_in" in token:
            expires_in = token["expires_in"]
            logger.info(f"В токен, полученном с сервера expires_in равен {expires_in}")
        else:
            expires_in = float("inf")
            logger.debug("expires_in нет в токен полученном с сервера")

        self.token_manager.save_tokens(
            self.access_token, self.refresh_token or "", expires_in
        )
        return self.access_token

    def refresh_access_token(self, depth: int = 0) -> str | None:
        """Обновляет access token с помощью refresh token"""
        if depth > 2:
            logger.warning("Превышена глубина рекурсии при обновлении токена")
            return None

        if not self.refresh_token:
            logger.error("Refresh token отсутствует")
            return None

        token_data = {
            "grant_type": REFRESH_TOKEN_IN_TOKEN,
            REFRESH_TOKEN_IN_TOKEN: self.refresh_token,
            "client_id": self.variables.get_var("YANDEX_CLIENT_ID"),
        }

        response = requests.post(
            self.variables.get_var("TOKEN_URL", "https://oauth.yandex.ru/token"),
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

        if response.status_code >= 400:
            logger.warning(f"Ошибка {response.status_code} при обновлении токена")
            return None

        token = response.json()
        self.access_token = token.get(C.ACCESS_TOKEN)
        self.token_state = "valid" if self.access_token else "invalid"

        if REFRESH_TOKEN_IN_TOKEN in token:
            self.refresh_token = token[REFRESH_TOKEN_IN_TOKEN]

        if "expires_in" in token:
            expires_in = token["expires_in"]
            self._token_expires_at = time.time() + expires_in - 60
        else:
            expires_in = float("inf")
            self._token_expires_at = float("inf")
            logger.info("expires_in отсутствует в token, полученном с сервера")

        self.token_manager.save_tokens(
            self.access_token, self.refresh_token or "", expires_in
        )

        return self.access_token if self.token_state == "valid" else None


class YandexOAuth:
    """Фасад для управления OAuth авторизацией"""

    def __init__(
        self,
        port: int,
    ):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        env_vars = EnvironmentVariables()
        self.token_manager = TokenManager(env_vars)
        self.flow = OAuthFlow(self.token_manager, port, env_vars)

    def get_token(self) -> str | None:
        """Получает действительный access token"""
        try:
            token = self.flow.get_access_token()
            if token:
                logger.info("Успешно получен access_token")
                return token
            else:
                logger.error("Не удалось получить access_token")
                return None
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            return None
