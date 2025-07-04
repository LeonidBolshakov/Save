from __future__ import annotations
import webbrowser
import os
import sys
import json
import logging
from dotenv import load_dotenv
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
from pathlib import Path
import argparse

# Глобальный logger для всей программы
logger: logging.Logger = logging.getLogger(__name__)


# Кастомные исключения
class AuthError(Exception):
    """Базовое исключение для ошибок авторизации"""


class AuthCancelledError(AuthError):
    """Исключение при отмене авторизации пользователем"""


class RefreshTokenError(AuthError):
    """Ошибка при обновлении токена"""


def configure_logging() -> None:
    """Настраивает глобальный logger"""
    global logger

    LOG_LEVELS: dict[str, int] = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    log_level_name = os.getenv("LOGGING_LEVEL", "info").lower()
    log_level = LOG_LEVELS.get(log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    logger.debug(f"Уровень логирования установлен в {logging.getLevelName(log_level)}")


def validate_environment_vars() -> None:
    """Проверяет наличие обязательных переменных окружения"""
    required_vars = ["YANDEX_CLIENT_ID", "YANDEX_REDIRECT_URI", "YANDEX_SCOPE"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Не заданы переменные окружения: {', '.join(missing)}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OAuth 2.0 авторизация для Яндекс.Диск",
        allow_abbrev=False,  # Запрещаем сокращения
        add_help=False,  # Отключаем автоматический --help
    )

    # Добавляем кастомный обработчик для --help
    parser.add_argument(
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Показать это сообщение и выйти",
    )

    parser.add_argument(
        "--tokens-file",
        default="tokens.json",
        help="Файл для сохранения токенов (по умолчанию: tokens.json)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=12345,
        help="Порт для callback-сервера (по умолчанию: 12345)",
    )

    # Парсим только известные аргументы
    return parser.parse_known_args()[0]


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
        """Обертка для обработки исключений"""
        try:
            super().handle()
        except Exception as e:
            logger.error(f"Ошибка обработки запроса: {e}")

    def log_message(self, format_: str, *args: Any) -> None:
        """Отключаем стандартное логирование запросов"""
        return

    def do_GET(self) -> None:
        server: OAuthHTTPServer = cast(OAuthHTTPServer, self.server)
        state: OAuthFlow = server.oauth_flow

        if "?" in self.path:
            state.callback_path = self.path
            state.callback_received = True

            # Запускаем shutdown в отдельном потоке (неблокирующий)
            threading.Thread(target=server.shutdown, daemon=True).start()

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            html: str = """
            <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 40px;">
                <h1 style="color: #4CAF50;">✅ Авторизация Яндекс.Диск прошла успешно!</h1>
                <p>Это окно можно закрыть</p>
                <button onclick="window.close()" 
                    style="padding: 12px 24px; 
                           background: #4CAF50; 
                           color: white; 
                           border: none; 
                           border-radius: 4px; 
                           cursor: pointer;
                           font-size: 16px;">
                Закрыть окно
                </button>
            </body></html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(204)
            self.end_headers()


class TokenManager:
    """Управляет сохранением и загрузкой токенов авторизации"""

    def __init__(self, tokens_file: Path):
        self.tokens_file = tokens_file
        self.last_check_result: bool | None = None

    def save_tokens(
        self, access_token: str, refresh_token: str, expires_in: int
    ) -> None:
        """Сохраняет токены с расчетом абсолютного времени истечения"""
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": time.time() + expires_in - 60,  # Запас 60 секунд
        }
        with open(self.tokens_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info("Токены сохранены в %s", self.tokens_file)

    def load_valid_tokens(self) -> dict | None:
        """Загружает токены только если файл существует и токены не истекли"""
        if not self.tokens_file.exists():
            logger.debug("Файл токенов не существует: %s", self.tokens_file)
            return None

        try:
            with open(self.tokens_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            required_keys = {"access_token", "expires_at"}
            if not required_keys.issubset(data.keys()):
                logger.warning(
                    "Файл токенов поврежден, отсутствуют ключи: %s",
                    required_keys - set(data.keys()),
                )
                return None

            current_time = time.time()
            if current_time >= data["expires_at"]:
                logger.warning(
                    "Токены истекли (просрочены на %.0f сек)",
                    current_time - data["expires_at"],
                )
                return None

            # Убрана проверка через API - полагаемся только на expires_at
            return data

        except json.JSONDecodeError:
            logger.error("Ошибка декодирования JSON в файле токенов")
            return None
        except Exception as e:
            logger.error("Непредвиденная ошибка загрузки токенов: %s", e)
            return None

    def validate_token_api(self, access_token: str) -> bool | None:
        """
        Проверяет валидность токена через запрос к API Яндекс. Диска

        Returns:
            True: токен валиден
            False: токен невалиден
            None: не удалось проверить (ошибка сети)
        """
        try:
            response = requests.get(
                "https://cloud-api.yandex.net/v1/disk",
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=5,
            )

            if response.status_code == 200:
                self.last_check_result = True
                return True

            if response.status_code in (401, 403):
                logger.debug(f"Недействительный токен (HTTP {response.status_code})")
                self.last_check_result = False
                return False

            logger.warning(
                f"Ошибка API при проверке токена: HTTP {response.status_code}"
            )
            self.last_check_result = None
            return None

        except requests.RequestException as e:
            logger.warning(f"Ошибка сети при проверке токена: {str(e)}")
            self.last_check_result = None
            return None


class OAuthFlow:
    """Управляет процессом OAuth 2.0 авторизации"""

    def __init__(
        self,
        token_manager: TokenManager,
        port: int,
    ):
        self.token_manager = token_manager
        self.port = port
        self.callback_received: bool = False
        self.callback_path: str | None = None
        self.refresh_token: str | None = None
        self.access_token: str | None = None
        self._token_expires_at: float = 0
        self.token_state: str = "unknown"  # valid, expired, invalid

    def get_access_token(self, depth: int = 0) -> str | None:
        """Рекурсивно получает токен с защитой от бесконечной рекурсии"""
        if depth > 3:
            logger.error("Превышена глубина рекурсии при получении токена")
            return None

        try:
            # 1. Проверка токена в памяти
            if (
                self.access_token
                and self.token_state == "valid"
                and not self.is_token_expired()
            ):
                return self.access_token

            # 2. Загрузка токенов из файла
            tokens = self.token_manager.load_valid_tokens()
            if tokens:
                self.access_token = tokens["access_token"]
                self.refresh_token = tokens.get("refresh_token")
                self._token_expires_at = tokens["expires_at"]
                self.token_state = "valid"  # Предполагаем валидность

                # Если токен истёк, обновляем его
                if self.is_token_expired():
                    if self.refresh_token:
                        return self.refresh_access_token(depth + 1)
                    return self.run_full_auth_flow()

                return self.access_token

            # 3. Попытка обновить токен
            if self.refresh_token:
                try:
                    return self.refresh_access_token(depth + 1)
                except RefreshTokenError:
                    self.refresh_token = None
                    self.token_state = "invalid"

            # 4. Полная аутентификация
            return self.run_full_auth_flow()

        except AuthCancelledError:
            return None
        except AuthError as e:
            logger.error(f"Ошибка авторизации: {e}")
            raise

    def is_token_expired(self) -> bool:
        """Проверяет, истек ли срок действия текущего токена"""
        return time.time() >= (self._token_expires_at - 30)

    def run_full_auth_flow(self) -> str:
        """Запускает полный процесс авторизации OAuth 2.0 с PKCE"""
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
            raise AuthCancelledError("Превышено время ожидания авторизации") from e
        except AuthCancelledError:
            raise
        except Exception as e:
            raise AuthError(f"Ошибка в процессе авторизации: {e}") from e

    @staticmethod
    def generate_pkce_params() -> tuple[str, str]:
        """Генерирует параметры PKCE для защиты потока авторизации"""
        logger.debug("Генерация параметров PKCE")
        code_verifier: str = secrets.token_urlsafe(64)
        code_challenge: str = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .replace("=", "")
        )
        return code_verifier, code_challenge

    @staticmethod
    def build_auth_url(code_challenge: str) -> str:
        """Формирует URL для запроса авторизации"""
        logger.debug("Формирование URL авторизации")
        client: WebApplicationClient = WebApplicationClient(
            os.getenv("YANDEX_CLIENT_ID")
        )
        return client.prepare_request_uri(
            os.getenv("AUTH_URL", "https://oauth.yandex.ru/authorize"),
            redirect_uri=os.getenv("YANDEX_REDIRECT_URI"),
            scope=os.getenv("YANDEX_SCOPE"),
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

    def start_auth_server(self) -> OAuthHTTPServer:
        """Запускает HTTP-сервер для обработки callback"""
        logger.info("Запускаю сервер на localhost:%d...", self.port)
        server: OAuthHTTPServer = OAuthHTTPServer(
            ("localhost", self.port), CallbackHandler, self
        )
        server_thread: threading.Thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        return server

    @staticmethod
    def open_browser(auth_url: str) -> None:
        """Открывает браузер для прохождения авторизации"""
        logger.info("Открываю браузер для авторизации Яндекс.Диск...")
        webbrowser.open(auth_url)

    def wait_for_callback(self) -> None:
        """Ожидает получения callback от OAuth-провайдера"""
        logger.info("Ожидаю авторизацию...")
        start_time: float = time.time()
        while not self.callback_received:
            if time.time() - start_time > 120:
                logger.error("Таймаут: не получил ответ за 2 минуты")
                raise TimeoutError("Таймаут: не получил ответ за 2 минуты")
            time.sleep(0.1)
        logger.info("Получен callback!")

    def parse_callback(self) -> str:
        """Извлекает код авторизации из callback URL"""
        if not self.callback_path:
            logger.error("Callback path не установлен")
            raise AuthCancelledError("Авторизация не была завершена")

        query: str = urlparse(self.callback_path).query
        params: dict[str, list[str]] = parse_qs(query)

        if "error" in params:
            error_code = params["error"][0]
            error_desc: str = params.get("error_description", ["Unknown error"])[0]

            if error_code == "access_denied":
                raise AuthCancelledError(
                    f"Пользователь отказал в авторизации: {error_desc}"
                )

            error_msg = f"Ошибка авторизации: {error_code} - {error_desc}"
            logger.error(error_msg)
            raise AuthError(error_msg)

        auth_code: str = params.get("code", [""])[0]
        if not auth_code:
            logger.error("Не удалось извлечь код авторизации")
            logger.debug(f"Полученные параметры: {params}")
            raise AuthError("Не удалось извлечь код авторизации")

        logger.info(f"Извлечен код: auth_code='{auth_code[:15]}...'")
        return auth_code

    def exchange_token(self, auth_code: str, code_verifier: str) -> str:
        """Обменивает код авторизации на токены доступа"""
        token_data: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": os.getenv("YANDEX_CLIENT_ID"),
            "code_verifier": code_verifier,
            "redirect_uri": os.getenv("YANDEX_REDIRECT_URI"),
        }

        logger.info("Получаю токен доступа...")
        try:
            response: requests.Response = requests.post(
                os.getenv("TOKEN_URL", "https://oauth.yandex.ru/token"),
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            token: dict[str, Any] = response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе токена: {e}")
            if hasattr(e, "response") and e.response:
                logger.debug(f"Ответ сервера: {e.response.text}")
            raise AuthError("Ошибка при обмене кода на токен") from e

        if "access_token" not in token:
            logger.error("Токен доступа не получен в ответе")
            logger.debug(f"Полученный ответ: {token}")
            raise AuthError("Токен доступа не получен в ответе")

        self.access_token = token["access_token"]
        self.refresh_token = token.get("refresh_token", self.refresh_token)

        if "expires_in" in token:
            expires_in = token["expires_in"]
            self.token_manager.save_tokens(
                self.access_token, self.refresh_token or "", expires_in
            )
            self._token_expires_at = time.time() + expires_in - 60

        # Убрана проверка через API - полагаемся на ответ сервера
        return self.access_token

    def refresh_access_token(self, depth: int = 0) -> str:
        """Обновляет access token с помощью refresh token"""
        if depth > 2:
            raise RefreshTokenError("Превышена глубина рекурсии при обновлении токена")

        if not self.refresh_token:
            logger.error("Попытка обновления без refresh token")
            raise RefreshTokenError("Refresh token отсутствует")

        logger.info("Обновляю токен доступа...")
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": os.getenv("YANDEX_CLIENT_ID"),
        }

        try:
            response = requests.post(
                os.getenv("TOKEN_URL", "https://oauth.yandex.ru/token"),
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            # Проверяем статус ответа
            if response.status_code >= 400:
                error_msg = f"Ошибка {response.status_code} при обновлении токена"
                logger.error(error_msg)
                logger.debug(f"Ответ сервера: {response.text}")
                raise RefreshTokenError(error_msg)

            response.raise_for_status()  # Дополнительная проверка
            token = response.json()

            # Обработка ответа
            self.access_token = token["access_token"]
            new_refresh_token = token.get("refresh_token")
            if new_refresh_token:
                logger.debug("Получен новый refresh token")
                self.refresh_token = new_refresh_token

            if "expires_in" in token:
                expires_in = token["expires_in"]
                self.token_manager.save_tokens(
                    self.access_token, self.refresh_token or "", expires_in
                )
                self._token_expires_at = time.time() + expires_in - 60

            self.token_state = "valid"
            return self.access_token

        except requests.RequestException as e:
            status_code = (
                e.response.status_code
                if hasattr(e, "response") and e.response
                else "N/A"
            )
            error_msg = f"Ошибка {status_code} при обновлении токена: {str(e)}"
            logger.error(error_msg)
            if hasattr(e, "response") and e.response:
                logger.debug(f"Ответ сервера: {e.response.text}")
            self.token_state = "invalid"
            raise RefreshTokenError(error_msg) from e

    @staticmethod
    def validate_token_api(access_token: str) -> bool | None:
        """
        Проверяет валидность токена через API Яндекс. Диска

        Returns:
            True: токен точно валиден (200 OK)
            False: токен точно невалиден (401/403)
            None: статус токена не определен (ошибки сети, сервера)
        """
        try:
            response = requests.get(
                "https://cloud-api.yandex.net/v1/disk",
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=5,
            )

            if response.status_code == 200:
                return True

            if response.status_code in (401, 403):
                logger.debug(f"Недействительный токен (HTTP {response.status_code})")
                return False

            logger.warning(
                f"Ошибка API при проверке токена: HTTP {response.status_code}"
            )
            return None

        except requests.RequestException as e:
            logger.warning(f"Ошибка сети при проверке токена: {str(e)}")
            return None


class YandexOAuth:
    """Фасад для управления OAuth-авторизацией Яндекс. Диск"""

    def __init__(
        self,
        tokens_file: str | Path,
        port: int,
    ):
        """
        Инициализирует OAuth-клиент

        :param tokens_file: Путь к файлу для сохранения токенов.
        :param port: Порт для callback-сервера.
        """
        # Разрешаем небезопасный транспорт для локальной разработки
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        load_dotenv()

        # Инициализация logger
        configure_logging()
        validate_environment_vars()

        # Создание зависимостей
        self.token_manager = TokenManager(Path(tokens_file))
        self.flow = OAuthFlow(self.token_manager, port)

    def get_token(self) -> str | None:
        """
        Основной метод: получает действительный access_token

        :return: Токен доступа или None если авторизация отменена
        """
        try:
            return self.flow.get_access_token()
        except AuthError as e:
            logger.critical(f"Ошибка авторизации: {e}")
            return None
        except Exception as e:
            logger.critical(f"Неизвестная ошибка: {e}")
            return None

    def refresh_token(self) -> str | None:
        """Явное обновление токена"""
        try:
            if self.flow.refresh_token:
                # Возвращаем результат обновления токена
                return self.flow.refresh_access_token()
            logger.warning("Refresh token отсутствует")
            return None
        except RefreshTokenError as e:
            logger.error(f"Ошибка обновления токена: {e}")
            return None


def main() -> None:
    """Основная точка входа в программу (CLI интерфейс)"""
    args = parse_arguments()

    try:
        # Инициализация объекта авторизации
        auth = YandexOAuth(
            tokens_file=args.tokens_file,
            port=args.port,
        )

        # Получение токена
        if token := auth.get_token():
            print(token)  # Вывод токена в stdout
            sys.exit(0)  # Успешное завершение
        else:
            logger.info("Авторизация отменена пользователем или проблемы с Internet")
            sys.exit(2)  # Код для отмены авторизации

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        sys.exit(1)  # Общий код ошибки


if __name__ == "__main__":
    main()
