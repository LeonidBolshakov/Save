import sys
import logging
from enum import Enum

logger = logging.getLogger(__name__)

from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.LOGGING.customstreamhandler import CustomStreamHandler
from SRC.LOGGING.customrotatingfilehandler import CustomRotatingFileHandler
from SRC.GENERAL.constants import Constants as C
from SRC.YADISK.yandexconst import YandexConstants as YC
from SRC.GENERAL.environment_variables import EnvironmentVariables


# Обозначения обработчиков логеров внутри класса
class HandlerLogger(Enum):
    file = "file"
    max_level = "max_level"
    console = "console"


class TuneLogger:
    def __init__(self):
        """Инициализация с использованием переменных окружения"""
        variables = EnvironmentVariables()

        self.log_level_name_for_console = variables.get_var(
            C.ENV_LOGGING_LEVEL_CONSOLE, C.DEFAULT_LOG_LEVEL
        ).lower()
        self.log_level_name_for_file = variables.get_var(
            C.ENV_LOGGING_LEVEL_FILE, C.DEFAULT_LOG_LEVEL
        ).lower()

        self.log_format = C.LOG_FORMAT  # Формат для всех обработчиков логгеров
        self.handlers_logger = {  # Словарь обработчиков логгеров
            HandlerLogger.file: self.create_file_handler(),
            HandlerLogger.max_level: MaxLevelHandler(),
            HandlerLogger.console: CustomStreamHandler(sys.stdout),
        }

    def setup_logging(self):
        """Настройка глобального логирования"""

        # Настройка уровней логирования
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
        variables = EnvironmentVariables()
        log_file_name = variables.get_var(C.ENV_LOG_FILE_NAME, C.LOG_FILE_NAME)

        return CustomRotatingFileHandler(
            filename=log_file_name,
            maxBytes=C.DEFAULT_LOG_MAX_BYTES,
            backupCount=C.DEFAULT_LOG_BACKUP_COUNT,
            encoding=C.ENCODING,
            delay=True,
        )

    def configure_handlers(
        self, log_format: str, log_level_console: int, log_level_file: int
    ) -> None:
        """Конфигурация всех обработчиков"""

        handlers = list(self.handlers_logger.values())

        # Настройка форматирования
        for handler in handlers:
            handler.setFormatter(logging.Formatter(log_format))
            handler.encoding = "utf-8"

        # Настройка уровней логирования
        self.handlers_logger[HandlerLogger.file].setLevel(log_level_file)
        self.handlers_logger[HandlerLogger.console].setLevel(log_level_console)
        self.handlers_logger[HandlerLogger.max_level].setLevel(logging.NOTSET)

        self.configure_root_handlers(handlers)

    @staticmethod
    def configure_root_handlers(handlers: list[logging.Handler]) -> None:
        """Добавление обработчиков к корневому логгеру"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        for handler in handlers:
            root_logger.addHandler(handler)
