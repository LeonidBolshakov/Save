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
from typing import Any, cast, Optional
import json
import traceback

# Разрешаем небезопасный транспорт для локальной разработки
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Конфигурация OAuth
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
        super().__init__(server_address, handler_class)
        self.oauth_flow: OAuthFlow = oauth_flow


class CallbackHandler(BaseHTTPRequestHandler):
    """Обработчик callback-запросов от OAuth-провайдера и запросов статуса"""

    def log_message(self, format_: str, *args: Any) -> None:
        """Отключаем стандартное логирование запросов"""
        return

    def do_GET(self) -> None:
        """Обработка GET-запросов"""
        server: OAuthHTTPServer = cast(OAuthHTTPServer, self.server)
        state: OAuthFlow = server.oauth_flow

        # Обработка запросов статуса
        if self.path == "/status":
            self.handle_status_request(state)
            return

        # Обработка callback от провайдера
        if "?" in self.path:
            self.handle_callback(state)
            return

        # Игнорируем другие запросы
        self.send_response(204)
        self.end_headers()

    def handle_status_request(self, state: OAuthFlow) -> None:
        """Обработка запросов статуса авторизации (long polling)"""
        # Устанавливаем соединение для long polling
        start_time = time.time()
        timeout = 30  # Максимальное время ожидания

        # Ждем изменения статуса или таймаута
        while time.time() - start_time < timeout:
            # Проверяем обновление статуса
            if state.authorization_status != "pending":
                break
            time.sleep(0.1)  # Проверяем каждые 100 мс

        # Формируем JSON-ответ
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        response = {
            "status": state.authorization_status,
            "message": state.authorization_message,
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def handle_callback(self, state: OAuthFlow) -> None:
        """Обработка callback от OAuth-провайдера"""
        # Сохраняем путь callback
        state.callback_path = self.path
        state.callback_received = True
        state.authorization_status = "processing"
        state.authorization_message = "Обработка кода авторизации..."

        # Отправляем страницу для отслеживания статуса
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Авторизация Яндекс.Диск</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 40px;
                    background-color: #f8f9fa;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #2196F3;
                    margin-bottom: 20px;
                }
                .status {
                    margin: 20px 0;
                    padding: 15px;
                    border-radius: 5px;
                    background-color: #e3f2fd;
                }
                .loader {
                    margin: 20px auto;
                    width: 50px;
                    height: 50px;
                    border: 5px solid #e0e0e0;
                    border-top: 5px solid #2196F3;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                .success {
                    color: #4CAF50;
                    background-color: #e8f5e9;
                }
                .error {
                    color: #f44336;
                    background-color: #ffebee;
                }
                .button {
                    padding: 12px 24px;
                    background: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                }
                .button:hover {
                    background: #0b7dda;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 id="title">Авторизация Яндекс.Диск</h1>
                <div id="status" class="status">
                    <div class="loader"></div>
                    <p>Идет процесс авторизации...</p>
                </div>
                <button id="closeButton" class="button" style="display:none;" onclick="window.close()">Закрыть окно</button>
            </div>

            <script>
                function checkStatus() {
                    fetch('/status')
                        .then(response => {
                            if (!response.ok) {
                                throw new Error('Ошибка сервера: ' + response.status);
                            }
                            return response.json();
                        })
                        .then(data => {
                            const statusElement = document.getElementById('status');
                            const titleElement = document.getElementById('title');
                            const buttonElement = document.getElementById('closeButton');

                            switch(data.status) {
                                case 'processing':
                                    statusElement.innerHTML = `
                                        <div class="loader"></div>
                                        <p>${data.message}</p>
                                    `;
                                    setTimeout(checkStatus, 1000);
                                    break;

                                case 'success':
                                    titleElement.textContent = '✅ Авторизация успешна!';
                                    titleElement.style.color = '#4CAF50';
                                    statusElement.className = 'status success';
                                    statusElement.innerHTML = `<p>${data.message}</p>`;
                                    buttonElement.style.display = 'block';
                                    break;

                                case 'error':
                                    titleElement.textContent = '❌ Ошибка авторизации';
                                    titleElement.style.color = '#f44336';
                                    statusElement.className = 'status error';
                                    statusElement.innerHTML = `<p>${data.message}</p>`;
                                    buttonElement.style.display = 'block';
                                    break;

                                default:
                                    statusElement.innerHTML = `
                                        <div class="loader"></div>
                                        <p>Ожидание обновления статуса...</p>
                                    `;
                                    setTimeout(checkStatus, 1000);
                            }
                        })
                        .catch(error => {
                            console.error('Ошибка при проверке статуса:', error);
                            // Повторяем запрос через 1 секунду
                            setTimeout(checkStatus, 1000);
                        });
                }

                // Начинаем проверку статуса при загрузке страницы
                document.addEventListener('DOMContentLoaded', checkStatus);
            </script>
        </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def do_POST(self) -> None:
        """Обработка POST-запросов для выключения сервера"""
        server: OAuthHTTPServer = cast(OAuthHTTPServer, self.server)
        if self.path == "/shutdown":
            self.send_response(200)
            self.end_headers()
            threading.Timer(1, server.shutdown).start()
        else:
            self.send_response(404)
            self.end_headers()


class OAuthFlow:
    """Управляет процессом OAuth 2.0 авторизации с PKCE"""

    TOKENS_FILE = "tokens.json"

    def __init__(self) -> None:
        """Инициализирует состояние потока авторизации"""
        self.callback_received: bool = False
        self.callback_path: str | None = None
        self.authorization_status: str = "pending"
        self.authorization_message: str = "Ожидание начала авторизации..."
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    @staticmethod
    def is_token_valid(token: str) -> bool:
        """Проверяет валидность access token"""
        try:
            response = requests.get(
                "https://cloud-api.yandex.net/v1/disk",
                headers={"Authorization": f"OAuth {token}"},
                timeout=10,
            )
            return response.status_code == 200
        except:
            return False

    def refresh_access_token(self) -> bool:
        """Обновляет access token с помощью refresh token"""
        if not self.refresh_token:
            return False

        try:
            response = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": YANDEX_CLIENT_ID,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data.get("access_token")
            # Новый refresh token может не возвращаться, тогда сохраняем старый
            self.refresh_token = token_data.get("refresh_token", self.refresh_token)

            if self.access_token:
                self.save_tokens()
                return True
            return False
        except Exception as e:
            print(f"❌ Ошибка при обновлении токена: {e}")
            return False

    def save_tokens(self) -> None:
        """Сохраняет текущие токены в файл"""
        if self.access_token and self.refresh_token:
            with open(self.TOKENS_FILE, "w") as f:
                json.dump(
                    {
                        "access_token": self.access_token,
                        "refresh_token": self.refresh_token,
                        "timestamp": int(time.time()),
                    },
                    f,
                )
            print(f"🔑 Токены сохранены в {self.TOKENS_FILE}")

    def load_tokens(self) -> bool:
        """Загружает токены из файла и проверяет их валидность"""
        try:
            with open(self.TOKENS_FILE, "r") as f:
                tokens = json.load(f)
                self.access_token = tokens["access_token"]
                self.refresh_token = tokens["refresh_token"]

                # Проверяем валидность токена
                if self.is_token_valid(self.access_token):
                    print("✅ Токены загружены из файла, access token действителен")
                    return True
                return False
        except:
            return False

    def run_oauth_flow(self) -> None:
        """Запускает процесс OAuth-авторизации для получения токенов"""
        server = None
        try:
            # Генерация PKCE параметров
            code_verifier: str = secrets.token_urlsafe(64)
            code_challenge: str = (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                )
                .decode()
                .replace("=", "")
            )

            # Создаем OAuth-клиент
            client: WebApplicationClient = WebApplicationClient(YANDEX_CLIENT_ID)

            # Формируем URL для авторизации с PKCE
            auth_url: str = client.prepare_request_uri(
                AUTH_URL,
                redirect_uri=YANDEX_REDIRECT_URI,
                scope=YANDEX_SCOPE,
                code_challenge=code_challenge,
                code_challenge_method="S256",
            )

            # Запускаем HTTP-сервер для обработки callback
            print("Запускаю сервер на localhost:12345...")
            server = OAuthHTTPServer(("localhost", 12345), CallbackHandler, self)
            server_thread: threading.Thread = threading.Thread(
                target=server.serve_forever
            )
            server_thread.daemon = True
            server_thread.start()

            # Открываем браузер для авторизации
            print("Открываю браузер для авторизации Яндекс.Диск...")
            webbrowser.open(auth_url)

            # Ожидаем получения callback (максимум 120 секунд)
            print("Ожидаю авторизацию...")
            start_time: float = time.time()
            while not self.callback_received:
                if time.time() - start_time > 120:
                    self.authorization_status = "error"
                    self.authorization_message = (
                        "Таймаут: не получили ответ за 2 минуты"
                    )
                    print("\n❌", self.authorization_message)
                    return
                time.sleep(0.1)

            # Обрабатываем полученный callback
            print("Получен callback!")
            query: str = cast(str, urlparse(self.callback_path).query)
            params: dict[str, list[str]] = parse_qs(query)

            # Проверяем наличие ошибки в параметрах
            if "error" in params:
                error_desc: str = params.get("error_description", ["Unknown error"])[0]
                self.authorization_status = "error"
                self.authorization_message = (
                    f"Ошибка авторизации: {params['error'][0]} - {error_desc}"
                )
                print(f"❌ Ошибка авторизации: {self.authorization_message}")
                return

            # Извлекаем код авторизации
            auth_code: str = params.get("code", [""])[0]
            if not auth_code:
                self.authorization_status = "error"
                self.authorization_message = "Не удалось извлечь код авторизации из URL"
                print(f"❌ {self.authorization_message}")
                print(f"Полученные параметры: {params}")
                return

            print(f"Извлечен код: auth_code='{auth_code[:15]}...'")
            self.authorization_status = "processing"
            self.authorization_message = "Получен код авторизации, обмен на токен..."

            # Формируем запрос для получения токена доступа
            token_data: dict[str, str] = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": YANDEX_CLIENT_ID,
                "code_verifier": code_verifier,
                "redirect_uri": YANDEX_REDIRECT_URI,
            }

            # Отправляем запрос на получение токена
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
                self.authorization_status = "error"
                self.authorization_message = f"Ошибка при получении токена: {str(e)}"
                print(f"❌ {self.authorization_message}")
                if hasattr(e, "response") and e.response:
                    print("Ответ сервера:", e.response.text)
                return

            # Сохраняем полученные токены
            self.access_token = token.get("access_token")
            self.refresh_token = token.get("refresh_token", "")

            if not self.access_token:
                self.authorization_status = "error"
                self.authorization_message = (
                    "Ошибка авторизации: токен доступа не получен"
                )
                print(f"❌ {self.authorization_message}")
                print("Полученный ответ:", token)
                return

            # Обновляем статус
            self.authorization_status = "success"
            self.authorization_message = (
                f"✅ Авторизация успешна!\n"
                f"Токен доступа: {self.access_token[:15]}..."
            )

            print("\n✅ Авторизация успешна!")
            print(f"Access Token: {self.access_token[:15]}...")
            if self.refresh_token:
                print(f"Refresh Token: {self.refresh_token[:15]}...")

            # Сохраняем токены в файл
            self.save_tokens()

        except Exception as e:
            self.authorization_status = "error"
            self.authorization_message = f"Непредвиденная ошибка: {str(e)}"
            print(f"❌ Непредвиденная ошибка: {e}")
            traceback.print_exc()
        finally:
            if server is not None:
                time.sleep(5)  # Даем время браузеру получить финальный статус
                server.shutdown()
                print("Завершаю работу сервера...")
            else:
                print("Сервер не был запущен, завершение без выключения сервера.")

    def main(self) -> Optional[str]:
        """Основной метод: возвращает действительный access token"""
        # Пробуем загрузить токены из файла
        if self.load_tokens():
            return self.access_token

        # Если токенов нет или они недействительны, пробуем обновить
        if self.refresh_token and self.refresh_access_token():
            return self.access_token

        # Если обновить не удалось, запускаем процесс авторизации
        self.run_oauth_flow()
        if self.access_token:
            return self.access_token

        return None


def check_disk_space(access_token_: str) -> Optional[float]:
    """Проверяет доступ к API Яндекс-Диска и возвращает общее пространство в GB"""
    try:
        print("Проверяю доступ к Яндекс.Диску...")
        response = requests.get(
            "https://cloud-api.yandex.net/v1/disk",
            headers={"Authorization": f"OAuth {access_token_}"},
            timeout=15,
        )
        response.raise_for_status()
        disk_info = response.json()
        total_space_gb = disk_info["total_space"] / (1024**3)
        print(f"Общее пространство: {total_space_gb:.2f} GB")
        return total_space_gb
    except Exception as e:
        print(f"❌ Ошибка доступа к API Яндекс.Диска: {str(e)}")
        return None


if __name__ == "__main__":
    flow = OAuthFlow()
    access_token = flow.main()

    if access_token:
        # Проверяем доступ к API (пункт 11) - вне класса
        disk_space = check_disk_space(access_token)
        if disk_space is not None:
            print(f"✅ Успешный доступ к Яндекс.Диску, доступно {disk_space:.2f} GB")
        else:
            print("❌ Не удалось получить доступ к Яндекс.Диску")
    else:
        print("❌ Не удалось получить действительный токен доступа")
