import sys
import logging

logger = logging.getLogger(__name__)

from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.MAIL.yagmailhandler import YaGmailHandler
from SRC.LOGGING.customstreamhandler import CustomStreamHandler
from SRC.LOGGING.customrotatingfilehandler import CustomRotatingFileHandler
from SRC.GENERAL.constants import Constants as C
from SRC.YADISK.yandexconst import YandexConstants as YC
from SRC.GENERAL.environment_variables import EnvironmentVariables

FILE = "file"
MAX_LEVEL = "max_level"
CONSOLE = "console"


class TuneLogger:
    def __init__(self):
        """Инициализация с использованием переменных окружения"""
        variables = EnvironmentVariables()

        self.sender_email = variables.get_var(C.ENV_SENDER_EMAIL)
        self.sender_password = variables.get_var(C.ENV_SENDER_PASSWORD)
        self.recipient_email = variables.get_var(C.ENV_RECIPIENT_EMAIL)
        self.log_level_name_for_console = variables.get_var(
            C.ENV_LOGGING_LEVEL_CONSOLE, C.DEFAULT_LOG_LEVEL
        ).lower()
        self.log_level_name_for_file = variables.get_var(
            C.ENV_LOGGING_LEVEL_FILE, C.DEFAULT_LOG_LEVEL
        ).lower()

        self.log_format = C.LOG_FORMAT  # Формат для всех обработчиков логгеров
        self.log_handlers = {  # Словарь обработчиков логгеров
            FILE: self.create_file_handler(),
            MAX_LEVEL: MaxLevelHandler(),
            CONSOLE: CustomStreamHandler(sys.stdout),
        }

    def setup_logging(self):
        """Настройка глобального логирования"""
        log_level_console = self.get_log_level_console()
        log_level_file = self.get_log_level_file()
        self.configure_handlers(self.log_format, log_level_console, log_level_file)

        # Для библиотек устанавливаем более высокий уровень
        for lib in YC.YANDEX_LIBS:
            logging.getLogger(lib).setLevel(C.DEFAULT_LEVEL_LIB)

    def get_log_level_console(self) -> int:
        """Определение уровня логирования на консоль"""

        return C.LOG_LEVELS.get(
            self.log_level_name_for_console, C.DEFAULT_LEVEL_GENERAL
        )

    def get_log_level_file(self) -> int:
        """Определение уровня логирования в файл"""

        return C.LOG_LEVELS.get(self.log_level_name_for_file, C.DEFAULT_LEVEL_GENERAL)

    @staticmethod
    def create_file_handler() -> CustomRotatingFileHandler:
        """Создание файлового обработчика"""
        return CustomRotatingFileHandler(
            filename=C.DEFAULT_LOG_FILE,
            maxBytes=C.DEFAULT_LOG_MAX_BYTES,
            backupCount=C.DEFAULT_LOG_BACKUP_COUNT,
            encoding=C.ENCODING,
            delay=True,
        )

    def create_email_handler(self):
        """Создание email обработчика"""
        return YaGmailHandler(
            self.sender_email, self.sender_password, self.recipient_email
        )

    def configure_handlers(
            self, log_format: str, log_level_console: int, log_level_file: int
    ) -> None:
        """Конфигурация всех обработчиков"""
        handlers = list(self.log_handlers.values())

        # Настройка форматирования
        for handler in handlers:
            handler.setFormatter(logging.Formatter(log_format))

        # Настройка уровней
        self.log_handlers[FILE].setLevel(log_level_file)
        self.log_handlers[MAX_LEVEL].setLevel(logging.NOTSET)
        self.log_handlers[CONSOLE].setLevel(log_level_console)

        self.configure_root_handlers(handlers)

    @staticmethod
    def configure_root_handlers(handlers: list[logging.Handler]) -> None:
        """Добавление обработчиков к корневому логгеру"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        for handler in handlers:
            root_logger.addHandler(handler)
