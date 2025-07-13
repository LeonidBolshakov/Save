import os
import sys
import logging
from dotenv import load_dotenv
import maxlevelhandler
from yagmailhandler import YaGmailHandler
from customstreamhandler import CustomStreamHandler
from customrotatingfilehandler import CustomRotatingFileHandler

logger = logging.getLogger(__name__)


class TuneLogger:
    # Общие настройки по умолчанию
    DEFAULT_LOG_LEVEL = "info"
    DEFAULT_LOG_FILE = "backup.log"
    DEFAULT_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
    DEFAULT_BACKUP_COUNT = 3

    def __init__(self):
        """Инициализация с загрузкой env-переменных"""
        load_dotenv()
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        self.sender_password = os.getenv("SENDER_PASSWORD", "")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL", "")
        self.log_level_name = os.getenv("LOGGING_LEVEL", self.DEFAULT_LOG_LEVEL).lower()

    def setup_logging(self):
        """Настройка глобального логирования"""
        log_format = "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
        log_level = self.get_log_level()
        self.configure_handlers(log_format, log_level)

        # Для библиотек устанавливаем более высокий уровень
        for lib in ["urllib3", "yadisk"]:
            logging.getLogger(lib).setLevel(logging.WARNING)

    def get_log_level(self) -> int:
        """Определение уровня логирования"""
        LOG_LEVELS = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }
        logger.debug(f"Уровень логирования: {self.log_level_name}")
        return LOG_LEVELS.get(self.log_level_name, logging.INFO)

    def create_file_handler(self) -> CustomRotatingFileHandler:
        """Создание файлового обработчика"""
        return CustomRotatingFileHandler(
            filename=self.DEFAULT_LOG_FILE,
            maxBytes=self.DEFAULT_MAX_BYTES,
            backupCount=self.DEFAULT_BACKUP_COUNT,
            encoding="utf-8",
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
