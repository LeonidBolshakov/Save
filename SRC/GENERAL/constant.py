import logging


class Constant(frozenset):
    ENV_YANDEX_CLIENT_ID = "BOL_SAVE_YANDEX_CLIENT_ID"

    ACCESS_TOKEN = "ACCESS_TOKEN"  # token доступа к Яндекс-Диску
    APP_NAME = "bol_save"
    ARCHIVE_SUFFIX = ".exe"
    AUTH_URL = "AUTH_URL"
    DEFAULT_7Z_PATHS = [
        "C:\\Program Files\\7-Zip\\7z.exe",
        "C:\\Program Files (x86)\\7-Zip\\7z.exe",
    ]
    DEFAULT_LEVEL_LIB = logging.WARNING
    DEFAULT_LEVEL_GENERAL = logging.INFO
    DEFAULT_CONFIG_FILE = "config_file.txt"
    DEFAULT_LOCAL_ARCHIVE_FILE = f"archive{ARCHIVE_SUFFIX}"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FILE = "save.log"
    DEFAULT_LOG_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
    DEFAULT_LOG_BACKUP_COUNT = 3
    DEFAULT_PORT = 12345
    DOTENV_PATH = "env"
    ENCODING = "utf-8"
    EMAIL_ERROR_CONTENT = (
        "🚨 Сообщение:\n\n"
        "Архивация провалилась.\n"
        "Максимальный уровень ошибки: {level_name}\n"
        "Подробности в LOG файле: {log_path}\n\n"
        "Время: {last_time_str}"
    )
    EMAIL_ERROR_SUBJECT = "🚨 Проблемы при сохранении данных"
    EMAIL_INFO_CONTENT = (
        "✅ Сообщение:\n\n"
        "Архив успешно записан в облако.\n"
        "Расположение: {remote_archive_path}\n\n"
        "Время: {last_time_str}"
    )
    EMAIL_INFO_SUBJECT = "✅ Успешное сохранение данных"
    EMAIL_WARNING_CONTENT = (
        "🔥 Сообщение:\n\nАрхив создан с предупреждениями.\n"
        "Расположение: {remote_archive_path}\n\n"
        "Проверьте LOG файл: {log_path}\n\n"
        "Время: {last_time_str}"
    )
    EMAIL_WARNING_SUBJECT = "🔥 Предупреждение при архивации"
    EMAIL_SEND_TRIGGER = "*Stop"
    ENV_CLIENT_SECRET = "BOL_SAVE_YANDEX_CLIENT_SECRET"
    ENV_LOGGING_LEVEL_CONSOLE = "LOGGING_LEVEL_CONSOLE"
    ENV_LOGGING_LEVEL_FILE = "LOGGING_LEVEL_FILE"
    ENV_PASSWORD_ARCHIVE = "BOL_SAVE_PASSWORD_ARCHIVE"
    ENV_RECIPIENT_EMAIL = "RECIPIENT_EMAIL"
    ENV_SENDER_EMAIL = "SENDER_EMAIL"
    ENV_SENDER_PASSWORD = "BOL_SAVE_SENDER_PASSWORD"
    EXPIRES_AT = "EXPIRES_AT"  # Время истечения токена
    GENERAL_REMOTE_ARCHIVE_FORMAT = (
            "{archive}" + "_{year}_{month:02d}_{day:02d}_{file_num}"
    )
    HTML_WINDOW_SUCCESSFUL = """
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
    LIBS = ["urllib3", "yadisk"]
    LIST_ARCHIVE_FILE = r"C:\PycharmProjects\Save\list.txt"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    LOG_LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    MAX_RETRY_ATTEMPTS = 3  # Максимальное количество попыток отправки email
    MISSING = " ** --> Отсутствуют"
    MONTHS_RU = [
        "",  # Пустой элемент для удобства индексации (месяцы с 1 по 12)
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]
    PATTERN_7_Z = "7z.exe"
    PRESENT = "Представлены"
    REFRESH_TOKEN = "REFRESH_TOKEN"  # refresh token к Яндекс-Диску
    REMOTE_ARCHIVE_PATH = "disk:/Архивы"
    REMOTE_ARCHIVE_PREFIX = "archive"
    REMOTE_LINK = "remote_path="
    RETRY_DELAY = 5  # Задержка между попытками отправки email (в секундах)
    SECRET_KEY_START = "BOL_SAVE_"
    STATE_INVALID = "invalid"
    STATE_UNKNOWN = "unknown"
    STATE_VALID = "valid"
    STOP_SERVICE_MESSAGE = (
        f"***** Не менять! Информация для отправки служебного сообщения "
        f"{EMAIL_SEND_TRIGGER} {REMOTE_LINK}"
    )
    TOKEN_URL = "TOKEN_URL"
    TOKEN_URL_DEFAULT = "https://oauth.yandex.ru/token"
    URL_API_YANDEX_DISK = "https://cloud-api.yandex.net/v1/disk"
    URL_AUTORIZATION_YANDEX_OAuth = "https://oauth.yandex.ru/authorize"
    VARS_KEYRING = [  # секретные переменные окружения
        f"{ENV_YANDEX_CLIENT_ID}",  # ID Яндекс клиента
        f"{ENV_SENDER_PASSWORD}",  # Почтовый пароль отправителя
        f"{ENV_PASSWORD_ARCHIVE}",  # Пароль создаваемого архива
        f"{ENV_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{ACCESS_TOKEN}",  # token доступа к Яндекс-Диску
        f"{REFRESH_TOKEN}",  # refresh token к Яндекс-Диску
        f"{EXPIRES_AT}",  # Время истечения токена
    ]
    VARS_REQUIRED = [  # Обязательные переменные окружения
        f"{ENV_YANDEX_CLIENT_ID}",  # ID OAuth-приложения Яндекс для API доступа
        f"{ENV_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{ENV_PASSWORD_ARCHIVE}",  # Пароль для шифрования архива
        f"{ENV_SENDER_EMAIL}",  # Email для отправки уведомлений
        f"{ENV_SENDER_PASSWORD}",  # Пароль от email отправителя
        f"{ENV_RECIPIENT_EMAIL}",  # Email получателя уведомлений
    ]
    YANDEX_REDIRECT_URI = "YANDEX_REDIRECT_URI"
    YANDEX_SCOPE = "YANDEX_SCOPE"
    YANDEX_SMTP_HOST = "smtp.yandex.ru"
    YANDEX_SMTP_PORT = 465
