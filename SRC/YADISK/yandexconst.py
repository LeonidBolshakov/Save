class YandexConstants(frozenset):
    YANDEX_ACCESS_TOKEN = "YANDEX_ACCESS_TOKEN"  # token доступа к Яндекс-Диску
    YANDEX_EXPIRES_AT = "YANDEX_EXPIRES_AT"  # Время истечения токена
    YANDEX_REFRESH_TOKEN = "YANDEX_REFRESH_TOKEN"  # refresh token к Яндекс-Диску
    YANDEX_REDIRECT_URI = "YANDEX_REDIRECT_URI"

    API_YANDEX_LOAD_FILE = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    ENV_YANDEX_CLIENT_ID = "YANDEX_CLIENT_ID"
    ENV_YANDEX_CLIENT_SECRET = "YANDEX_CLIENT_SECRET"
    MISSING = " ** --> Отсутствуют"
    PRESENT = "Представлены"
    URL_API_YANDEX_DISK = "https://cloud-api.yandex.net/v1/disk"
    URL_AUTORIZATION_YANDEX_OAuth = "https://oauth.yandex.ru/authorize"
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
    YANDEX_SCOPE = "cloud_api:disk.app_folder cloud_api:disk.read cloud_api:disk.write"
    YANDEX_TOKEN_URL = "https://oauth.yandex.ru/token"
