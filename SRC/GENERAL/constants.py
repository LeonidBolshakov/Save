import logging

from SRC.YADISK.yandexconst import YandexConstants as YC


class Constants(frozenset):
    LOCAL_ARCHIVE_PREFIX = "archive"
    REMOTE_ARCHIVE_PREFIX = "archive"

    APP_NAME = "bol_save"
    ARCHIVE_SUFFIX = ".exe"
    COMPRESSION_LEVEL = 5
    CONFIG_FILE_PATH = "config_file_path.txt"
    CONFIG_KEY_SEVEN_ZIP_PATH = "SEVEN_ZIP_PATH"
    STANDARD_7Z_PATHS = [
        "C:\\Program Files\\7-Zip\\7z.exe",
        "C:\\Program Files (x86)\\7-Zip\\7z.exe",
    ]
    DEFAULT_LEVEL_LIB = logging.WARNING
    DEFAULT_LOG_BACKUP_COUNT = 3
    DEFAULT_LOG_LEVEL = logging.INFO
    DEFAULT_LOG_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
    ENV_STANDARD_PROGRAM_PATHS = "STANDARD_PROGRAM_PATHS"
    DOTENV_PATH = r"_INTERNAL/env"
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
    EMAIL_SEND_TRIGGER = "*Stop"
    EMAIL_WARNING_CONTENT = (
        "🔥 Сообщение:\n\nАрхив создан с предупреждениями.\n"
        "Расположение: {remote_archive_path}\n\n"
        "Проверьте LOG файл: {log_path}\n\n"
        "Время: {last_time_str}"
    )
    EMAIL_WARNING_SUBJECT = "🔥 Предупреждение при архивации"
    ENCODING = "utf-8"
    ENV_ARCHIVE_SUFFIX = "ARCHIVE_SUFFIX"
    ENV_COMPRESSION_LEVEL = "COMPRESSION_LEVEL"
    ENV_CONFIG_FILE_PATH = "CONFIG_FILE"
    ENV_LIST_ARCHIVE_FILE_PATH = "LIST_ARCHIVE_FILE_PATH"
    ENV_LOCAL_ARCHIVE_FILE_NAME = "LOCAL_ARCHIVE_FILE_NAME"
    ENV_LOG_FILE_NAME = "LOG_FILE_NAME"
    ENV_LOGGING_LEVEL_CONSOLE = "LOGGING_LEVEL_CONSOLE"
    ENV_LOGGING_LEVEL_FILE = "LOGGING_LEVEL_FILE"
    ENV_PASSWORD_ARCHIVE = "BOL_SAVE_PASSWORD_ARCHIVE"
    ENV_PATTERN_7Z = "PATTERN_7Z"
    ENV_PATTERN_PROGRAMME = "PATTERN_PROGRAMME"
    ENV_PROGRAMME_WRITE_FILE = "PROGRAMME_WRITE_FILE"
    ENV_RECIPIENT_EMAIL = "RECIPIENT_EMAIL"
    ENV_REMOTE_ARCHIVING_PREFIX = "REMOTE_ARCHIVE_PREFIX"
    ENV_ROOT_REMOTE_ARCHIVE_DIR = "ROOT_REMOTE_ARCHIVE_DIR"
    ENV_SENDER_EMAIL = "SENDER_EMAIL"
    ENV_SENDER_PASSWORD = "BOL_SAVE_SENDER_PASSWORD"
    GENERAL_REMOTE_ARCHIVE_FORMAT = "{archive}_{year}_{month}_{day}_{file_num}"
    LIST_ARCHIVE_FILE_PATCH = "_INTERNAL/list.txt"
    LOCAL_ARCHIVE_FILE_NAME = f"{LOCAL_ARCHIVE_PREFIX}{ARCHIVE_SUFFIX}"
    LOG_FILE_NAME = "save.log"
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
    PATTERN_PROGRAMME = "7z.exe"
    PROGRAMME_WRITE_FILE = "write_file_to_yandex_disk"
    ROOT_REMOTE_ARCHIVE_DIR = "/Архивы"
    REMOTE_LINK = "remote_path="
    RETRY_DELAY = 5  # Задержка между попытками отправки email (в секундах)
    SECRET_KEY_START = "BOL_SAVE_"
    STOP_SERVICE_MESSAGE = (
        f"***** Не менять! Информация для отправки служебного сообщения "
        f"{EMAIL_SEND_TRIGGER} {REMOTE_LINK}"
    )

    VARS_KEYRING = [  # секретные переменные окружения
        f"{YC.ENV_YANDEX_CLIENT_ID}",  # ID Яндекс клиента
        f"{YC.ENV_YANDEX_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{YC.YANDEX_ACCESS_TOKEN}",  # Токен доступа Яндекс
        f"{YC.YANDEX_REDIRECT_URI}",  # REDIRECT_URI из
        f"{YC.YANDEX_REFRESH_TOKEN}",  # refresh token к Яндекс-Диску
        f"{YC.YANDEX_REDIRECT_URI}",
        f"{ENV_SENDER_PASSWORD}",  # Почтовый пароль отправителя
        f"{ENV_PASSWORD_ARCHIVE}",  # Пароль создаваемого архива
    ]
    VARS_REQUIRED = [  # Обязательные переменные окружения
        f"{ENV_PASSWORD_ARCHIVE}",  # Пароль для шифрования архива
        f"{ENV_SENDER_EMAIL}",  # Email для отправки уведомлений
        f"{ENV_SENDER_PASSWORD}",  # Пароль от email отправителя
        f"{ENV_RECIPIENT_EMAIL}",  # Email получателя уведомлений
        f"{YC.ENV_YANDEX_CLIENT_ID}",  # ID OAuth-приложения Яндекс для API доступа
        f"{YC.ENV_YANDEX_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{YC.YANDEX_REDIRECT_URI}",
    ]
    YANDEX_SMTP_HOST = "smtp.yandex.ru"
    YANDEX_SMTP_PORT = 465
