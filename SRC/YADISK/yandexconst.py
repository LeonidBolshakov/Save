class YandexConstants(frozenset):
    YANDEX_ACCESS_TOKEN = "YANDEX_ACCESS_TOKEN"  # token доступа к Яндекс-Диску
    YANDEX_EXPIRES_AT = "YANDEX_EXPIRES_AT"  # Время истечения токена
    YANDEX_REFRESH_TOKEN = "YANDEX_REFRESH_TOKEN"  # refresh token к Яндекс-Диску

    API_YANDEX_LOAD_FILE = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    ENV_YANDEX_CLIENT_ID = "BOL_SAVE_YANDEX_CLIENT_ID"
    ENV_YANDEX_CLIENT_SECRET = "BOL_SAVE_YANDEX_CLIENT_SECRET"
    ENV_YANDEX_PORT = "BOL_SAVE_YANDEX_PORT"
    URL_API_YANDEX_DISK = "https://cloud-api.yandex.net/v1/disk"
    URL_AUTORIZATION_YANDEX_OAuth = "https://oauth.yandex.ru/authorize"
    YANDEX_VARS_KEYRING = [  # секретные переменные окружения
        f"{ENV_YANDEX_CLIENT_ID}",  # ID Яндекс клиента
        f"{ENV_YANDEX_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{ENV_YANDEX_PORT}",  # Номер порта, заданный в приложении Яндекс
        f"{YANDEX_ACCESS_TOKEN}",  # token доступа к Яндекс-Диску
        f"{YANDEX_REFRESH_TOKEN}",  # refresh token к Яндекс-Диску
        f"{YANDEX_EXPIRES_AT}",  # Время истечения токена
    ]
    YANDEX_VARS_REQUIRED = [  # Обязательные переменные окружения
        f"{ENV_YANDEX_CLIENT_ID}",  # ID OAuth-приложения Яндекс для API доступа
        f"{ENV_YANDEX_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{ENV_YANDEX_PORT}",  # Номер порта, заданный в приложении Яндекс
    ]
    YANDEX_AUTH_URL = "AUTH_URL"
    YANDEX_HTML_WINDOW_SUCCESSFUL = """
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
    YANDEX_LIBS = ["urllib3", "yadisk"]
    YANDEX_REDIRECT_URI = "YANDEX_REDIRECT_URI"
    YANDEX_SCOPE = "YANDEX_SCOPE"
    YANDEX_SMTP_HOST = "smtp.yandex.ru"
    YANDEX_SMTP_PORT = 465
    YANDEX_TOKEN_URL = "YANDEX_TOKEN_URL"
    YANDEX_TOKEN_URL_DEFAULT = "https://oauth.yandex.ru/token"
