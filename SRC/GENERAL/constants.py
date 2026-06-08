import logging

from SRC.YADISK.yandexconst import YandexConstants as YC


class Constants(frozenset):
    ARCHIVING_END_TRIGGER = "*Stop"
    CONFIG_FILE_WITH_PROGRAM_NAME_DEF = r"C:\TEMP\config_file_path.txt"
    CONSOLE_LOG_LEVEL_DEF = "WARNING"
    CONVERT_LOGGING_NAME_TO_CODE = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
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
    EMAIL_RETRY_DELAY_IN_SEC = 5  # Задержка между попытками отправки email (в секундах)
    EMAIL_SMTP_HOST = "smtp.yandex.ru"
    EMAIL_SMTP_PORT = 465
    EMAIL_WARNING_SUBJECT = "🔥 Предупреждение при архивации"
    ENCODING = "utf-8"
    ENV_ARCHIVER_STANDARD_PROGRAM_PATHS = "ARCHIVER_STANDARD_PROGRAM_PATHS"
    ENV_CONFIG_FILE_WITH_PROGRAM_NAME = "CONFIG_FILE_WITH_PROGRAM_NAME_DEF"
    ENV_CONSOLE_LOG_LEVEL = "CONSOLE_LOG_LEVEL"
    ENV_FILE_LOG_LEVEL = "FILE_LOG_LEVEL"
    ENV_FULL_ARCHIVER_NAME = "FULL_ARCHIVER_NAME"
    ENV_LOCAL_ARCHIVE_FILE_NAME = "LOCAL_ARCHIVE_FILE_NAME"
    ENV_LOCAL_ARCHIVE_SUFFIX = "LOCAL_ARCHIVE_SUFFIX"
    ENV_LOG_FILE_PATH = "LOG_FILE_NAME"
    ENV_LOG_SETUP_FILE_PATH = "LOG_SETUP_FILE_PATH"
    ENV_LOG_SETUP_LEVEL = "LOG_SETUP_LEVEL"
    ENV_PASSWORD_ARCHIVE = "PASSWORD_ARCHIVE"
    ENV_PROGRAMME_WRITE_FILE = "PROGRAMME_WRITE_FILE"
    ENV_RECIPIENT_EMAIL = "RECIPIENT_EMAIL"
    ENV_REMOTE_ARCHIVING_PREFIX = "REMOTE_ARCHIVE_PREFIX_DEF"
    ENV_ROOT_REMOTE_ARCHIVE_DIR = "ROOT_REMOTE_ARCHIVE_DIR"
    ENV_SENDER_EMAIL = "SENDER_EMAIL"
    ENV_SENDER_PASSWORD = "SENDER_PASSWORD"
    ENV_SEVEN_Z_COMPRESSION_LEVEL = "SEVEN_Z_COMPRESSION_LEVEL"
    FILE_LOG_LEVEL_DEF = "INFO"
    FULL_NAME_SEVEN_Z = "7z.exe"
    GENERAL_REMOTE_ARCHIVE_FORMAT = "{archive}_{year}_{month}_{day}_{file_num}"
    KEYRING_APP_NAME = "bol_save"
    LINK_REMOTE_ARCHIVE = "remote_path="
    LIST_NAMS_OF_ARCHIVABLE_FILES = "list.txt"
    LOCAL_ARCHIVE_PREFIX_DEF = "archive"

    LOCAL_ARCHIVE_SUFFIX_DEF = ".7z"
    LOCAL_ARCHIVE_FILE_NAME_DEF = (
        f"{LOCAL_ARCHIVE_PREFIX_DEF}{LOCAL_ARCHIVE_SUFFIX_DEF}"
    )
    LOG_FILE_PATH_DEF = r"C:\TEMP\save.log"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    LOG_LEVEL_FOR_LIBRARIES = logging.WARNING
    LOG_SETUP_FILE_PATH_DEF = "C:\\TEMP\\save_setup.log"
    LOG_SETUP_LEVEL_DEF = "DEBUG"
    MASK_DEFAULT = "1111111"
    MASK_ERROR = "Ошибка при задании маски дней недели"

    MONTHS_RU = [
        "",  # Заглушка для нулевого месяца. Нумерация месяцев начинается с 1.
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
    NULL = "\x00"
    PAR___ARCHIVER = (
        "Archiver"  # Параметр формируется дочерним классом buckup_manager.abc
    )
    PAR___SEARCH_PROGRAMME = (
        "SearchProgramme"  # Параметр формируется дочерним классом buckup_manager.abc
    )
    PAR_ARCHIVE_DIR = "archive_dir"
    PAR_ARCHIVE_EXTENSION = "archive_extension"
    PAR_ARCHIVE_PATH = "archive_path"
    PAR_ARCHIVER_NAME = "archiver_name"
    PAR_COMPRESSION_LEVEL = "compression_level"
    CONFIG_FILE_WITH_PROGRAM_NAME = r"C:\TEMP\config_file_path.txt"
    PAR_LIST_ARCHIVE_FILE_PATHS = "list_archive_file_paths"
    PAR_LOCAL_ARCHIVE_NAME = "local_archive_name"
    PAR_PASSWORD = "password"
    PAR_STANDARD_PROGRAM_PATHS = "standard_program_paths"
    PROGRAM_PATH = "PROGRAM_PATH"
    PROGRAM_PATH_DEFAULT = r"C:\Program Files\Bolshakov\save_to_cload\main.exe"
    PROGRAM_PATH_ERROR = "Ошибка в пути выполняемой программы"
    PROGRAM_WRITE_VARS = "write_vars"
    REMOTE_ARCHIVE_PREFIX_DEF = "archive"
    ROOT_REMOTE_ARCHIVE_DIR = "/Архивы"
    ROTATING_BACKUP_COUNT = 3
    ROTATING_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
    SEND_MAIL_MAX_RETRY_ATTEMPTS = 3  # Максимальное количество попыток отправки email
    SETTINGS_DIRECTORY = r"Bolshakov\save\_internal"
    SEVEN_Z_COMPRESSION_LEVEL_DEF = 5
    SEVEN_Z_STANDARD_PATHS = [
        "C:\\Program Files\\7-Zip\\7z.exe",
        "C:\\Program Files (x86)\\7-Zip\\7z.exe",
    ]
    SCHEDULED_DAYS_MASK = "SCHEDULED_DAYS_MASK"
    START_TASK_DEFAULT = "12:30"
    START_TASK_ERROR = "Ошибка в задании времени старта программы"
    STOP_SERVICE_MESSAGE = (
        f"***** Не менять! Информация для отправки служебного сообщения "
        f"{ARCHIVING_END_TRIGGER}"
        f"{LINK_REMOTE_ARCHIVE}"
    )
    TASK_CREATED_SUCSESSFULL = "Задача создана успешно"
    TASK_CREATED_ERROR = "Ошибка создания задачи"
    TASK_DAYS = "TASK_DAYS"
    TASK_DELETED_ERROR = "Ошибка удаления задачи"
    TASK_DELETED_SUCSESSFULL = "Задача удалена успешно"
    TASK_DESCRIPTION = "TASK_DESCRIPTION"
    TASK_DESCRIPTION_DEFAULT = "Ежедневное сохранение данных"
    TASK_DESCRIPTION_ERROR = "Описание задачи планировщика содержит символ '\x00'"
    TASK_FOLDER = "TASK_FOLDER"
    TASK_FOLDER_ERROR = "Ошибка в директории задачи планировщика"
    TASK_FOLDER_DEFAULT = r"\Bolshakov"
    TASK_NAME = "TASK_NAME"
    TASK_NAME_DEFAULT = "save"
    TASK_NAME_ERROR = "Ошибка в имени задачи планировщика"
    TASK_NOT_READY_TO_CREATED = (
        "Задача не может быть создана."
        "\nИсправьте ошибочные параметры в env файле."
        "\nПодробности записаны в LOG файл."
    )
    TASK_START_IN = "TASK_START_IN"
    TASK_READY_TO_CREATED = (
        "Задача пока не создана."
        "\nДля создания задачи нажмите кнопку:"
        "\n'Создать задачу'"
    )
    TEXT_EMPTY = ""
    TEXT_ERROR = "Текст содержит символ \x00. Символ удалён из текста"
    TEXT_IS_DIRTY = "Данные были изменены, но не сохранены в задаче"
    TEXT_NO_DAY = "Выберите хотя бы один день недели."
    TEXT_NOT_TASK = (
        "Папка или задача планировщика не заданы. Проверьте настройки по умолчанию"
    )
    TEXT_TASK_MANUAL_EDIT = (
        "Задача планировщика {task} корректировалась вручную"
        "\nОтмените ручные правки или удалите задачу"
    )
    TEXT_REJECT_DATA = "Данные приведены в первоначальное состояние"
    VARIABLES_DOTENV_NAME_DEF = "env"
    VARS_KEYRING = [  # секретные переменные окружения
        f"{YC.ENV_YANDEX_CLIENT_ID}",  # ID Яндекс клиента
        f"{YC.ENV_YANDEX_CLIENT_SECRET}",  # Секретный ключ клиента
        f"{YC.YANDEX_ACCESS_TOKEN}",  # Токен доступа Яндекс
        f"{YC.YANDEX_REDIRECT_URI}",  # REDIRECT_URI из
        f"{YC.YANDEX_REFRESH_TOKEN}",  # refresh token к Яндекс-Диску
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
    WORK_DIRECTORY_PATH = "WORK_DIRECTORY_PATH"
    WORK_DIRECTORY_ERROR = "Ошибка в пути рабочей директории"
