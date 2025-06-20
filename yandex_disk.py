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
from typing import Any, cast, Tuple, Optional
from pathlib import Path
import argparse


def configure_logging() -> logging.Logger:
    """Настраивает и возвращает logger с динамическим уровнем логирования"""
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
    logger = logging.getLogger(__name__)
    logger.debug("Уровень логирования установлен в %s", logging.getLevelName(log_level))
    return logger


def validate_environment_vars() -> None:
    """Проверяет наличие обязательных переменных окружения"""
    required_vars = ["YANDEX_CLIENT_ID", "YANDEX_REDIRECT_URI", "YANDEX_SCOPE"]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Не заданы переменные окружения: {', '.join(missing)}")


def parse_arguments() -> argparse.Namespace:
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(
        description="OAuth 2.0 авторизация для Яндекс.Диск"
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
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Не открывать браузер автоматически",
    )
    return parser.parse_args()


class OAuthHTTPServer(HTTPServer):
    """Кастомный HTTP-сервер для OAuth-авторизации с хранилищем состояния

    Args:
        server_address: Кортеж (хост, порт) для запуска сервера
        handler_class: Класс для обработки HTTP-запросов
        oauth_flow: Экземпляр OAuthFlow для управления состоянием авторизации
    """

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
            logger = logging.getLogger(__name__)
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
            threading.Timer(1, server.shutdown).start()

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

    def save_tokens(
        self, access_token: str, refresh_token: str, expires_in: int
    ) -> None:
        """Сохраняет токены и время их действия в файл

        Args:
            access_token: Токен доступа для API
            refresh_token: Токен для обновления access_token
            expires_in: Время жизни access_token в секундах
        """
        data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": time.time() + expires_in - 60,  # Запас 60 секунд
        }
        with open(self.tokens_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logging.getLogger(__name__).info("Токены сохранены")

    def load_tokens(self) -> Optional[dict]:
        """Загружает токены из файла, если они действительны

        Returns:
            dict: Словарь с токенами и временем истечения, если токены действительны
            None: Если файл не существует или токены истекли
        """
        logger = logging.getLogger(__name__)
        try:
            if not self.tokens_file.exists():
                logger.debug("Файл токенов не существует")
                return None

            with open(self.tokens_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Проверяем срок действия access_token
            if time.time() < data["expires_at"]:
                logger.info("Использую сохранённые токены")
                return data

            logger.warning("Access token истёк")
            return None

        except Exception as e:
            logger.error(f"Ошибка загрузки токенов: {e}")
            return None


class OAuthFlow:
    """Управляет процессом OAuth 2.0 авторизации и обновлением токенов

    Args:
        token_manager: Экземпляр менеджера токенов
        port: Порт для callback-сервера
        open_browser: Открывать ли браузер автоматически
    """

    def __init__(
        self, token_manager: TokenManager, port: int = 12345, open_browser: bool = True
    ):
        self.token_manager = token_manager
        self.port = port
        self.open_browser_flag = open_browser
        self.callback_received: bool = False
        self.callback_path: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.access_token: Optional[str] = None
        self.token_expired: bool = False  # Новый флаг для отслеживания истекшего токена

    def get_access_token(self) -> str:
        """
        Основной метод для получения access_token

        Процесс:
        1. Пробует загрузить сохранённые токены
        2. Если токен истек и есть refresh_token, пробует обновить токены
        3. Если есть refresh_token, пробует обновить токены
        4. Если не удалось, запускает полный процесс авторизации

        Returns:
            str: Валидный access_token для доступа к API

        Raises:
            Exception: Если не удалось получить токен любым способом
        """
        logger = logging.getLogger(__name__)

        # Пробуем загрузить сохранённые токены
        tokens = self.token_manager.load_tokens()
        if tokens:
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]

            # Если токен помечен как истёкший, пробуем обновить
            if self.token_expired and self.refresh_token:
                try:
                    logger.info("Попытка обновить истёкший токен")
                    return self.refresh_access_token()
                except Exception as e:
                    logger.warning(f"Не удалось обновить истёкший токен: {e}")

            return self.access_token

        # Пробуем обновить токены, если есть refresh_token
        if self.refresh_token:
            try:
                logger.info("Попытка обновить токен с помощью refresh_token")
                return self.refresh_access_token()
            except Exception as e:
                logger.warning(f"Не удалось обновить токен: {e}")

        # Если ничего не помогло, запускаем полную авторизацию
        return self.run_full_auth_flow()

    def run_full_auth_flow(self) -> str:
        """Запускает полный процесс авторизации OAuth 2.0 с PKCE

        Returns:
            str: Полученный access_token

        Steps:
        1. Генерация PKCE параметров
        2. Формирование URL авторизации
        3. Запуск сервера для приема callback
        4. Открытие браузера для авторизации
        5. Обработка callback и получение кода авторизации
        6. Обмен кода на токены доступа
        """
        code_verifier, code_challenge = self.generate_pkce_params()
        auth_url = self.build_auth_url(code_challenge)
        self.start_auth_server()

        if self.open_browser_flag:
            self.open_browser(auth_url)

        self.wait_for_callback()
        auth_code = self.parse_callback()
        return self.exchange_token(auth_code, code_verifier)

    @staticmethod
    def generate_pkce_params() -> Tuple[str, str]:
        """Генерирует параметры PKCE для защиты потока авторизации

        Returns:
            Tuple[str, str]: (code_verifier, code_challenge)
            code_verifier: Случайная строка (64 байта)
            code_challenge: Хеш SHA256 от code_verifier в base64url формате
        """
        logger = logging.getLogger(__name__)
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
        """Формирует URL для запроса авторизации

        Args:
            code_challenge: Сгенерированный PKCE challenge

        Returns:
            str: Полный URL для запроса авторизации
        """
        logger = logging.getLogger(__name__)
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
        """Запускает HTTP-сервер для обработки callback

        Returns:
            OAuthHTTPServer: Экземпляр запущенного сервера
        """
        logger = logging.getLogger(__name__)
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
        """Открывает браузер для прохождения авторизации

        Args:
            auth_url: URL для запроса авторизации
        """
        logger = logging.getLogger(__name__)
        logger.info("Открываю браузер для авторизации Яндекс.Диск...")
        webbrowser.open(auth_url)

    def wait_for_callback(self) -> None:
        """Ожидает получения callback от OAuth-провайдера

        Raises:
            TimeoutError: Если callback не получен в течение 2 минут
        """
        logger = logging.getLogger(__name__)
        logger.info("Ожидаю авторизацию...")
        start_time: float = time.time()
        while not self.callback_received:
            if time.time() - start_time > 120:
                logger.error("Таймаут: не получил ответ за 2 минуты")
                raise TimeoutError("Таймаут: не получил ответ за 2 минуты")
            time.sleep(0.1)
        logger.info("Получен callback!")

    def parse_callback(self) -> str:
        """Извлекает код авторизации из callback URL

        Returns:
            str: Код авторизации

        Raises:
            ValueError: Если callback_path не установлен
            RuntimeError: Если провайдер вернул ошибку
            ValueError: Если код авторизации не найден
        """
        logger = logging.getLogger(__name__)
        if not self.callback_path:
            logger.error("Callback path не установлен")
            raise ValueError("Callback path не установлен")

        query: str = urlparse(self.callback_path).query
        params: dict[str, list[str]] = parse_qs(query)

        if "error" in params:
            error_desc: str = params.get("error_description", ["Unknown error"])[0]
            error_msg = f"Ошибка авторизации: {params['error'][0]} - {error_desc}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        auth_code: str = params.get("code", [""])[0]
        if not auth_code:
            logger.error("Не удалось извлечь код авторизации")
            logger.debug(f"Полученные параметры: {params}")
            raise ValueError("Не удалось извлечь код авторизации")

        logger.info(f"Извлечен код: auth_code='{auth_code[:15]}...'")
        return auth_code

    def exchange_token(self, auth_code: str, code_verifier: str) -> str:
        """Обменивает код авторизации на токены доступа

        Args:
            auth_code: Код авторизации, полученный от провайдера
            code_verifier: Исходный PKCE verifier

        Returns:
            str: Полученный access_token

        Raises:
            requests.RequestException: При ошибке сетевого запроса
            ValueError: Если токен доступа не получен
        """
        logger = logging.getLogger(__name__)
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
            raise

        if "access_token" not in token:
            logger.error("Токен доступа не получен в ответе")
            logger.debug(f"Полученный ответ: {token}")
            raise ValueError("Токен доступа не получен в ответе")

        # Сохраняем токены
        self.access_token = token["access_token"]
        self.refresh_token = token.get("refresh_token", self.refresh_token)

        # Сохраняем токены в файл
        if "expires_in" in token:
            self.token_manager.save_tokens(
                self.access_token, self.refresh_token or "", token["expires_in"]
            )

        # Проверяем доступ к API
        self.validate_token(self.access_token)

        return self.access_token

    def refresh_access_token(self) -> str:
        """Обновляет access token с помощью refresh token

        Returns:
            str: Обновлённый access_token

        Raises:
            ValueError: Если refresh token отсутствует
            requests.RequestException: При ошибке сетевого запроса
            RuntimeError: При невалидном refresh token
        """
        logger = logging.getLogger(__name__)
        if not self.refresh_token:
            logger.error("Попытка обновления без refresh token")
            raise ValueError("Refresh token отсутствует")

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
            response.raise_for_status()
            token = response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            if hasattr(e, "response") and e.response:
                logger.debug(f"Ответ сервера: {e.response.text}")
            raise

        # Обновляем токены
        self.access_token = token["access_token"]
        new_refresh_token = token.get("refresh_token")
        if new_refresh_token:
            logger.debug("Получен новый refresh token")
            self.refresh_token = new_refresh_token

        # Сохраняем новые токены
        if "expires_in" in token:
            self.token_manager.save_tokens(
                self.access_token, self.refresh_token or "", token["expires_in"]
            )

        # Проверяем доступ к API
        self.validate_token(self.access_token)

        return self.access_token

    @staticmethod
    def validate_token(access_token: str) -> None:
        """Проверяет валидность токена через запрос к API Яндекс.Диска

        Args:
            access_token: Токен для проверки

        Raises:
            requests.RequestException: При ошибке запроса к API
        """
        logger = logging.getLogger(__name__)
        logger.info("Проверяю доступ к Яндекс.Диску...")
        try:
            response = requests.get(
                "https://cloud-api.yandex.net/v1/disk",
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=15,
            )
            response.raise_for_status()
            disk_info: dict[str, Any] = response.json()
            total_space_gb: float = disk_info["total_space"] / (1024**3)
            logger.info(f"Общее пространство: {total_space_gb:.2f} GB")
            logger.info("Проверка доступа успешна")
        except requests.RequestException as e:
            logger.error(f"Ошибка доступа к API Яндекс.Диска: {e}")
            if hasattr(e, "response") and e.response:
                logger.debug(f"Ответ сервера: {e.response.text}")
            raise


def create_oauth_flow(args: argparse.Namespace) -> OAuthFlow:
    """Фабрика для создания экземпляра OAuthFlow"""
    token_manager = TokenManager(Path(args.tokens_file))
    return OAuthFlow(
        token_manager=token_manager, port=args.port, open_browser=not args.no_browser
    )


def main() -> None:
    """Основная точка входа в программу"""
    # Разрешаем небезопасный транспорт для локальной разработки
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    load_dotenv()

    # Инициализация
    logger = configure_logging()
    args = parse_arguments()

    try:
        validate_environment_vars()
        flow = create_oauth_flow(args)
        access_token = flow.get_access_token()
        print(access_token)  # Полный access_token в stdout

    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
