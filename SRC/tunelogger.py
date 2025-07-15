import os
import sys
import logging
from dotenv import load_dotenv
import maxlevelhandler
from yagmailhandler import YaGmailHandler
from customstreamhandler import CustomStreamHandler
from customrotatingfilehandler import CustomRotatingFileHandler

logger = logging.getLogger(__name__)

from constant import Constant as C


class TuneLogger:
    def __init__(self):
        """Инициализация с загрузкой env-переменных"""
        load_dotenv()
        self.sender_email = os.getenv(C.ENV_SENDER_EMAIL, "")
        self.sender_password = os.getenv(C.ENV_SENDER_PASSWORD, "")
        self.recipient_email = os.getenv(C.ENV_RECIPIENT_EMAIL, "")
        self.log_level_name = os.getenv(
            C.ENV_LOGGING_LEVEL, C.DEFAULT_LOG_LEVEL
        ).lower()
        self.log_format = C.LOG_FORMAT

    def setup_logging(self):
        """Настройка глобального логирования"""
        log_level = self.get_log_level()
        self.configure_handlers(self.log_format, log_level)

        # Для библиотек устанавливаем более высокий уровень
        for lib in C.LIBS:
            logging.getLogger(lib).setLevel(C.DEFAULT_LEVEL_LIB)

    def get_log_level(self) -> int:
        """Определение уровня логирования"""

        logger.debug(f"Уровень логирования: {self.log_level_name}")
        return C.LOG_LEVELS.get(self.log_level_name, C.DEFAULT_LEVEL_GENERAL)

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

    def configure_handlers(self, log_format: str, log_level: int) -> None:
        """Конфигурация всех обработчиков"""
        handlers = [
            self.create_file_handler(),
            maxlevelhandler.MaxLevelHandler(),
            CustomStreamHandler(sys.stdout),
        ]

        # Настройка форматирования и уровней
        for handler in handlers:
            handler.setFormatter(logging.Formatter(log_format))
            handler.setLevel(
                logging.DEBUG if isinstance(handler, YaGmailHandler) else log_level
            )

        self.configure_root_handlers(handlers)

    @staticmethod
    def configure_root_handlers(handlers: list[logging.Handler]) -> None:
        """Добавление обработчиков к корневому логгеру"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        for handler in handlers:
            root_logger.addHandler(handler)
