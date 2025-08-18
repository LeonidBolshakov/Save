import sys
from pathlib import Path
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
        self.variables = EnvironmentVariables()

        self.console_log_level = self.get_log_level(
            C.ENV_CONSOLE_LOG_LEVEL, C.CONSOLE_LOG_LEVEL_DEF
        )
        self.file_log_level = self.get_log_level(
            C.ENV_FILE_LOG_LEVEL, C.FILE_LOG_LEVEL_DEF
        )

        self.log_format = C.LOG_FORMAT  # Формат для всех обработчиков логгеров
        self.handlers_logger = {  # Словарь обработчиков логгеров
            HandlerLogger.file: self.create_file_handler(),
            HandlerLogger.max_level: MaxLevelHandler(),
            HandlerLogger.console: CustomStreamHandler(sys.stdout),
        }

    def get_log_level(
        self,
        env_name_handler: str,
        default_name_handler: str,
    ) -> int:
        """Определяет уровень логирования заданного для обработчика

        :param env_name_handler: Имя переменной, сообщаемое пользователю при запросе значения
        :param default_name_handler: Значение переменной по умолчанию
        :return: Уровень логирования
        """

        log_level_name = self.variables.get_var(
            env_name_handler, default_name_handler
        ).upper()
        return C.CONVERT_LOGGING_NAME_TO_CODE.get(log_level_name, logging.DEBUG)

    def setup_logging(self):
        """Настройка глобального логирования"""

        # Настройка уровней логирования
        self.configure_handlers(
            self.log_format, self.console_log_level, self.file_log_level
        )

        # Для сторонних библиотек устанавливаем более высокий уровень логирования
        for lib in YC.YANDEX_LIBS:
            logging.getLogger(lib).setLevel(C.LOG_LEVEL_FOR_LIBRARIES)

    @staticmethod
    def create_file_handler() -> CustomRotatingFileHandler:
        """Создание файлового обработчика"""
        variables = EnvironmentVariables()
        log_file_path = variables.get_var(C.ENV_LOG_FILE_PATH, C.LOG_FILE_PATH_DEF)

        p = Path(log_file_path)
        mode = "w" if (not p.exists() or p.stat().st_size == 0) else "a"

        return CustomRotatingFileHandler(
            filename=log_file_path,
            mode=mode,
            maxBytes=C.ROTATING_MAX_BYTES,
            backupCount=C.ROTATING_BACKUP_COUNT,
            encoding="utf-8-sig",
            delay=True,
        )

    def configure_handlers(
        self, log_format: str, log_level_console: int, file_log_level: int
    ) -> None:
        """Конфигурация всех обработчиков"""

        handlers = list(self.handlers_logger.values())

        # Настройка форматирования
        for handler in handlers:
            handler.setFormatter(logging.Formatter(log_format))

        # Настройка уровней логирования
        self.handlers_logger[HandlerLogger.file].setLevel(file_log_level)
        self.handlers_logger[HandlerLogger.console].setLevel(log_level_console)
        self.handlers_logger[HandlerLogger.max_level].setLevel(logging.NOTSET)

        self.configure_root_handlers(handlers)

    def configure_root_handlers(self, handlers: list[logging.Handler]) -> None:
        """Добавление обработчиков к корневому логгеру"""
        self._remove_loging()  # Удаление всех прежних обработчиков

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        for handler in handlers:
            root_logger.addHandler(handler)

    @staticmethod
    def _remove_loging() -> None:
        """Удаление настроек логирования"""
        logger_root = logging.getLogger()
        for handler in logger_root.handlers[:]:
            logger_root.removeHandler(handler)
