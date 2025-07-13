import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import secrets
import base64
import hashlib
from urllib.parse import urlparse, parse_qs

# Генерация PKCE
code_verifier = secrets.token_urlsafe(64)
code_challenge = (
    base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
    .decode()
    .replace("=", "")
)


# Обработчик запросов
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format_, *args):
        return

    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)

        if "code" in params:
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                "Авторизация Яндекс.Диск прошла успешно.\nВкладку можно закрыть".encode(
                    "utf-8"
                )
            )
            # Сохраняем код в сервере
            self.server.auth_code = params["code"][0]

        else:
            self.send_error(400, "Код авторизации не создан")


# Создаем сервер с явным атрибутом
# noinspection PyTypeChecker
server = HTTPServer(("localhost", 12345), Handler)
server.auth_code = None

# Запускаем процесс авторизации
webbrowser.open(
    "https://oauth.yandex.ru/authorize?"
    f"response_type=code&client_id=46e7a99ef2d6482ba87b8799df736906&"
    f"redirect_uri=http://localhost:12345&"
    f"code_challenge={code_challenge}&code_challenge_method=S256&"
    f"scope=cloud_api:disk.app_folder%20cloud_api:disk.read%20cloud_api:disk.write"
)

# Ожидаем callback
server.handle_request()

# Проверяем получение кода
if server.auth_code is None:
    raise RuntimeError("Authorization code not received")

# Обмен кода на токен
response = requests.post(
    "https://oauth.yandex.ru/token",
    data={
        "grant_type": "authorization_code",
        "code": server.auth_code,
        "client_id": "46e7a99ef2d6482ba87b8799df736906",
        "code_verifier": code_verifier,
    },
).json()

access_token = response["access_token"]
refresh_token = response["refresh_token"]

disk_info = requests.get(
    "https://cloud-api.yandex.net/v1/disk",
    headers={"Authorization": f"OAuth {access_token}"},
).json()

print(f"Total space: {disk_info['total_space'] / 1024 ** 3:.2f} GB")
