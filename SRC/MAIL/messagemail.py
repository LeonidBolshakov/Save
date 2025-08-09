from logging import Formatter, FileHandler, StreamHandler
import time
from datetime import datetime
import sys
import logging

from SRC.MAIL.yagmailhandler import YaGmailHandler
from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.LOGGING.tunelogger import TuneLogger
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T

# Инициализация логгера для текущего модуля
logger = logging.getLogger(__name__)


class MessageMail:
    """Класс для управления отправкой email-уведомлений на основе логов."""

    def __init__(self):
        """Инициализирует обработчик email с учетными данными из переменных окружения."""
        # Получение учетных данных из переменных окружения
        self.months_ru = C.MONTHS_RU
        self.max_retry_attempts = C.SEND_MAIL_MAX_RETRY_ATTEMPTS
        self.retry_delay = C.EMAIL_RETRY_DELAY_IN_SEC
        # Инициализация обработчика email (YaGmailHandler)
        self.email_handler = self.create_email_handler()

    @staticmethod
    def create_email_handler() -> YaGmailHandler:
        _variables = EnvironmentVariables()
        sender = _variables.get_var(C.ENV_SENDER_EMAIL, "")
        password = _variables.get_var(C.ENV_SENDER_PASSWORD, "")
        recipient = _variables.get_var(C.ENV_RECIPIENT_EMAIL, "")
        return YaGmailHandler(sender, password, recipient)

    def compose_and_send_email(self) -> bool:
        """Метод для формирования и отправки email с обработкой ошибок.
        Включает несколько попыток отправки при неудаче.

        :return: True при удачной отправке письма, False - при неудачной.
        """
        try:
            max_level_handler = MaxLevelHandler()
            max_level = max_level_handler.get_highest_level()
            last_time = max_level_handler.get_last_time()
            remote_archive_path = max_level_handler.get_remote_archive_path()
            subject, content = self._compose_message_content(
                last_time, max_level, remote_archive_path
            )
        except Exception as e:
            logger.error(T.error_compose_message.format(e=e))
            return False
        else:
            logger.info(T.start_send_email.format(subject=subject))
            return self._send_email_with_retry(subject, content)

    def _compose_message_content(
        self, last_time: float, max_level: int, remote_archive_path: str
    ) -> tuple[str, str]:
        """Формирует тему и содержание email в зависимости от уровня важности."""
        level_name = logging.getLevelName(max_level)
        last_time_str = self._format_timestamp(last_time)
        log_path = self._get_log_path()

        # Выбор шаблона email в зависимости от уровня логирования
        # noinspection PyUnreachableCode
        match max_level:
            case logging.NOTSET | logging.DEBUG | logging.INFO:
                return self._create_info_email(last_time_str, remote_archive_path)
            case logging.WARNING:
                return self._create_warning_email(
                    last_time_str, remote_archive_path, log_path
                )
            case _:  # Для ERROR, CRITICAL и других уровней
                return self._create_error_email(last_time_str, level_name, log_path)

    @staticmethod
    def _create_info_email(
        last_time_str: str, remote_archive_path: str
    ) -> tuple[str, str]:
        """Создает email-уведомление об успешном выполнении операции."""
        # noinspection PyUnusedLocal
        subject = C.EMAIL_INFO_SUBJECT
        content = C.EMAIL_INFO_CONTENT.format(
            remote_archive_path=remote_archive_path, last_time_str=last_time_str
        )
        return subject, content

    @staticmethod
    def _create_warning_email(
        last_time_str: str, remote_archive_path: str, log_path: str | None
    ) -> tuple[str, str]:
        """Создает email-уведомление с предупреждением."""
        # noinspection PyUnusedLocal
        subject = C.EMAIL_WARNING_SUBJECT
        content = C.EMAIL_WARNING_CONTENT.format(
            remote_archive_path=remote_archive_path,
            log_path=log_path,
            last_time_str=last_time_str,
        )
        return subject, content

    @staticmethod
    def _create_error_email(
        last_time_str: str, level_name: str, log_path: str | None
    ) -> tuple[str, str]:
        """Создает email-уведомление об ошибке."""
        subject = C.EMAIL_ERROR_SUBJECT
        content = C.EMAIL_ERROR_CONTENT.format(
            level_name=level_name, log_path=log_path, last_time_str=last_time_str
        )
        return subject, content

    def _format_timestamp(self, timestamp: float) -> str:
        """Конвертирует timestamp в читаемую дату на русском языке."""
        dt = datetime.fromtimestamp(timestamp)
        return f"{dt.day} {self.months_ru[dt.month]} {dt.year} года {dt:%H:%M}"

    @staticmethod
    def _get_log_path() -> str | None:
        """Находит и возвращает путь к файлу лога, если он настроен."""
        for handler in logging.getLogger().handlers:
            if isinstance(handler, FileHandler):
                return handler.baseFilename
        return None

    def _send_email_with_retry(self, subject: str, content: str) -> bool:
        """Выполняет отправку email с несколькими попытками при неудаче."""
        for attempt in range(1, self.max_retry_attempts + 1):
            try:
                if self.email_handler.send_email(subject, content):
                    return True
            except Exception as e:
                logger.error(T.error_send_email.format(e=e))

            if attempt < self.max_retry_attempts:
                time.sleep(C.EMAIL_RETRY_DELAY_IN_SEC)

        logger.error(T.failed_send_email)
        return False


def setup_logging(log_file: str = C.LOG_FILE_NAME_DEF):
    """
    Настраивает систему логирования с выводом в консоль и файл.
    Действует после завершения работы основной системы логирования
    """

    tune_logger = TuneLogger()
    formatter = Formatter(C.LOG_FORMAT)

    # Обработчик для вывода в консоль (только сообщения уровня INFO и выше)
    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(tune_logger.console_log_level)

    # Обработчик для записи в файл (все сообщения уровня DEBUG и выше)
    file_handler = FileHandler(log_file, encoding=C.ENCODING)
    file_handler.setLevel(tune_logger.file_log_level)

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    console_handler.setFormatter(formatter)

    # Удаление существующих обработчиков
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Добавление новых обработчиков
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_email_credentials() -> tuple[str, str, str]:
    _variables = EnvironmentVariables()
    """Получает и проверяет учетные данные для отправки email."""
    sender = _variables.get_var(C.ENV_SENDER_EMAIL, "")
    password = _variables.get_var(C.ENV_SENDER_PASSWORD, "")
    recipient = _variables.get_var(C.ENV_RECIPIENT_EMAIL, "")

    if not sender or not password:
        logging.error(T.missing_email_credentials)
        sys.exit(1)

    return sender, password, recipient


def run_test_scenarios() -> None:
    """Выполняет тестовые сценарии для проверки системы логирования."""
    logger.info("Система запущена")
    try:
        1 / 0  # Генерация ошибки деления на ноль
    except Exception as e:
        logger.error(f"Ошибка вычисления: {e}", exc_info=True)
    logger.warning("Ресурсы на исходе")
    logger.critical("Критическая ситуация!")
    logger.info("Команда *Stop* - отправка отчета")


def main() -> None:
    """Точка входа в приложение - выполняет настройку и тестовые сценарии."""
    try:
        setup_logging()
        run_test_scenarios()
    except Exception as e:
        logging.critical(f"Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
