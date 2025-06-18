from __future__ import annotations
import webbrowser
import os
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

# Разрешаем небезопасный транспорт для локальной разработки
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Конфигурация OAuth
load_dotenv()
YANDEX_CLIENT_ID: str = os.getenv("YANDEX_CLIENT_ID")
YANDEX_REDIRECT_URI: str = os.getenv("YANDEX_REDIRECT_URI")
YANDEX_SCOPE: str = os.getenv("YANDEX_SCOPE")
AUTH_URL: str = "https://oauth.yandex.ru/authorize"
TOKEN_URL: str = "https://oauth.yandex.ru/token"

required_vars = ["YANDEX_CLIENT_ID", "YANDEX_REDIRECT_URI", "YANDEX_SCOPE"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise EnvironmentError(f"Не заданы переменные окружения: {', '.join(missing)}")


class OAuthHTTPServer(HTTPServer):
    """Кастомный HTTP-сервер для OAuth-авторизации с хранилищем состояния"""

    def __init__(
            self, server_address: tuple[str, int], handler_class: Any, oauth_flow: OAuthFlow
    ) -> None:
        """
        Инициализирует сервер авторизации OAuth

        :param server_address: Адрес сервера (хост, порт)
        :param handler_class: Класс обработчика запросов (CallBack)
        :param oauth_flow: Экземпляр потока авторизации
        """
        super().__init__(server_address, handler_class)
        self.oauth_flow: OAuthFlow = oauth_flow


class CallbackHandler(BaseHTTPRequestHandler):
    """Обработчик callback-запросов от OAuth-провайдера"""

    def log_message(self, format_: str, *args: Any) -> None:
        """Отключаем стандартное логирование запросов"""
        return

    def do_GET(self) -> None:
        """
        Обрабатывает GET-запросы:
        - Запросы с параметрами (callback) сохраняют состояние и завершают процесс
        - Другие запросы игнорируются
        """
        # Приводим тип сервера к нашему кастомному классу
        server: OAuthHTTPServer = cast(OAuthHTTPServer, self.server)
        state: OAuthFlow = server.oauth_flow

        # Проверяем наличие параметров запроса (ожидаемый callback)
        if "?" in self.path:
            # Сохраняем путь callback и помечаем как полученный
            state.callback_path = self.path
            state.callback_received = True

            # Запланировать выключение сервера через 1 секунду
            threading.Timer(1, server.shutdown).start()

            # Отправляем пользователю страницу успешной авторизации
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
            # Игнорируем запросы без параметров (например, /favicon.ico)
            self.send_response(204)
            self.end_headers()


class OAuthFlow:
    """Управляет процессом OAuth 2.0 авторизации с PKCE"""

    def __init__(self) -> None:
        """Инициализирует состояние потока авторизации"""
        self.callback_received: bool = False
        self.callback_path: str | None = None

    def main(self) -> None:
        """
        Основной процесс авторизации:
        1. Генерация PKCE параметров
        2. Формирование URL авторизации
        3. Запуск сервера для приема callback
        4. Открытие браузера для авторизации
        5. Обработка callback и получение токена
        6. Проверка доступа к API
        """
        # 1. Генерация PKCE параметров
        code_verifier: str = secrets.token_urlsafe(64)
        code_challenge: str = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .decode()
            .replace("=", "")
        )

        # 2. Создаем OAuth-клиент
        client: WebApplicationClient = WebApplicationClient(YANDEX_CLIENT_ID)

        # 3. Формируем URL для авторизации с PKCE
        auth_url: str = client.prepare_request_uri(
            AUTH_URL,
            redirect_uri=YANDEX_REDIRECT_URI,
            scope=YANDEX_SCOPE,
            code_challenge=code_challenge,
            code_challenge_method="S256",
        )

        # 4. Запускаем HTTP-сервер для обработки callback
        print("Запускаю сервер на localhost:12345...")
        server: OAuthHTTPServer = OAuthHTTPServer(
            ("localhost", 12345), CallbackHandler, self
        )
        server_thread: threading.Thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # 5. Открываем браузер для авторизации
        print("Открываю браузер для авторизации Яндекс.Диск...")
        webbrowser.open(auth_url)

        # 6. Ожидаем получения callback (максимум 120 секунд)
        print("Ожидаю авторизацию...")
        start_time: float = time.time()
        while not self.callback_received:
            # Проверяем таймаут
            if time.time() - start_time > 120:
                print("\n❌ Таймаут: не получил ответ за 2 минуты")
                server.shutdown()
                return
            time.sleep(0.1)

        # 7. Обрабатываем полученный callback
        print("Получен callback!")
        query: str = cast(str, urlparse(self.callback_path).query)
        params: dict[str, list[str]] = parse_qs(query)

        # Проверяем наличие ошибки в параметрах
        if "error" in params:
            error_desc: str = params.get("error_description", ["Unknown error"])[0]
            print(f"❌ Ошибка авторизации: {params['error'][0]} - {error_desc}")
            return

        # Извлекаем код авторизации
        auth_code: str = params.get("code", [""])[0]
        if not auth_code:
            print("❌ Не удалось извлечь код авторизации из URL")
            print(f"Полученные параметры: {params}")
            return
        print(f"Извлечен код: auth_code='{auth_code[:15]}...'")

        # 8. Формируем запрос для получения токена доступа
        token_data: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": YANDEX_CLIENT_ID,
            "code_verifier": code_verifier,
            "redirect_uri": YANDEX_REDIRECT_URI,
        }

        # 9. Отправляем запрос на получение токена
        print("Получаю токен доступа...")
        try:
            response: requests.Response = requests.post(
                TOKEN_URL,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            token: dict[str, Any] = response.json()
        except Exception as e:
            print(f"❌ Ошибка при получении токена: {e}")
            if hasattr(e, "response") and e.response:
                print("Ответ сервера:", e.response.text)
            return

        # 10. Проверяем наличие токена доступа в ответе
        if "access_token" not in token:
            print("❌ Ошибка авторизации: токен доступа не получен")
            print("Полученный ответ:", token)
            return

        access_token: str = token["access_token"]
        refresh_token: str = token.get("refresh_token", "")

        # 11. Проверяем доступ к API Яндекс. Диска
        print("Проверяю доступ к Яндекс.Диску...")
        try:
            response = requests.get(
                "https://cloud-api.yandex.net/v1/disk",
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=15,
            )
            response.raise_for_status()
        except Exception as e:
            print(f"❌ Ошибка доступа к API Яндекс.Диска: {e}")
            print("Ответ сервера:", response.text if response else "Нет ответа")
            return

        # 12. Выводим информацию об успешной авторизации
        disk_info: dict[str, Any] = response.json()
        print("\n✅ Авторизация успешна!")
        print(f"Access Token: {access_token[:15]}...")
        if refresh_token:
            print(f"Refresh Token: {refresh_token[:15]}...")
        total_space_gb: float = disk_info["total_space"] / (1024 ** 3)
        print(f"Общее пространство: {total_space_gb:.2f} GB")


if __name__ == "__main__":
    flow: OAuthFlow = OAuthFlow()
    flow.main()
