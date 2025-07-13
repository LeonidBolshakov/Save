from logging import LogRecord, Formatter, FileHandler, StreamHandler
import time
from datetime import datetime
import sys
import os
import logging

from yagmailhandler import YaGmailHandler

logger = logging.getLogger(__name__)

# Константы
MONTHS_RU = [
    "",
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
DEFAULT_LOG_FILE = "application.log"
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5


class MessageMail:
    def __init__(self):
        """Получает учетные данные email из переменных окружения"""
        sender = os.getenv("SENDER_EMAIL", "")
        password = os.getenv("SENDER_PASSWORD", "")
        recipient = os.getenv("RECIPIENT_EMAIL", "")

        self.email_handler = YaGmailHandler(sender, password, recipient)

    def compose_and_send_email(self, record: LogRecord, max_level: int) -> None:
        """Формирует и отправляет e-mail"""

        subject, content = self._compose_message_content(record, max_level)
        if not self._send_email_with_retry(subject, content):
            error_msg = "Все попытки отправки email провалились"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
        logging.info("Служебное сообщение отправлено по e-mail")

    def _compose_message_content(
        self, record: LogRecord, max_level: int
    ) -> tuple[str, str]:
        """Формирует тему и содержание email"""
        level_name = logging.getLevelName(max_level)

        # noinspection PyUnreachableCode
        match max_level:
            case logging.DEBUG | logging.INFO:
                return self._create_info_email(record)
            case logging.WARNING:
                return self._create_warning_email(record)
            case _:
                return self._create_error_email(record, level_name)

    def _create_info_email(self, record: LogRecord) -> tuple[str, str]:
        """Формирует email для информационных сообщений"""
        archive_path = self._extract_archive_path(record.getMessage())
        subject = "✅ Успешное сохранение данных"
        content = (
            f"✅ Сообщение:\n\n "
            f"Архив успешно записан в облако.\n"
            f"Расположение: {archive_path}\n\n"
            f"Время: {self._format_timestamp(record.created)}"
        )
        return subject, content

    def _create_warning_email(self, record: LogRecord) -> tuple[str, str]:
        """Формирует email для предупреждений"""
        archive_path = self._extract_archive_path(record.getMessage())
        subject = "🔥 Предупреждение при архивации"
        content = (
            f"🔥 Сообщение:\n\nАрхив создан с предупреждениями.\n"
            f"Расположение: {archive_path}\n\n"
            f"Проверьте LOG файл: {self._get_log_path()}\n\n"
            f"Время: {self._format_timestamp(record.created)}"
        )
        return subject, content

    def _create_error_email(
        self, record: LogRecord, level_name: str
    ) -> tuple[str, str]:
        """Формирует email для ошибок"""
        subject = "🚨 Проблемы при сохранении данных"
        content = (
            f"🚨 Сообщение:\n\nАрхивация провалилась.\n"
            f"Максимальный уровень ошибки: {level_name}\n"
            f"Подробности в LOG файле: {self._get_log_path()}\n\n"
            f"Время: {self._format_timestamp(record.created)}"
        )
        return subject, content

    @staticmethod
    def _extract_archive_path(message: str) -> str:
        """Извлекает путь к архиву из сообщения"""
        if "remote_path=" in message:
            return message.split("remote_path=")[1]
        return ""

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        """Форматирует timestamp в русский формат даты"""
        dt = datetime.fromtimestamp(timestamp)
        return f"{dt.day} {MONTHS_RU[dt.month]} {dt.year} года {dt:%H:%M}"

    @staticmethod
    def _get_log_path() -> str | None:
        """Возвращает путь к файлу лога"""
        for handler in logging.getLogger().handlers:
            if isinstance(handler, FileHandler):
                return handler.baseFilename
        return None

    def _send_email_with_retry(self, subject: str, content: str) -> bool:
        """Пытается отправить email с повторными попытками"""
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            if self.email_handler.send_email(subject, content):
                return True
            if attempt < MAX_RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
        return False


def setup_logging(log_file: str = DEFAULT_LOG_FILE):
    """Настраивает систему логирования"""
    formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def get_email_credentials() -> tuple[str, str, str]:
    """Получает учетные данные email из переменных окружения"""
    sender = os.getenv("SENDER_EMAIL", "")
    password = os.getenv("SENDER_PASSWORD", "")
    recipient = os.getenv("RECIPIENT_EMAIL", "")

    if not sender or not password:
        logging.critical("Отсутствуют учетные данные email")
        sys.exit(1)

    return sender, password, recipient


def configure_email_logging() -> None:
    """Настраивает email логирование"""
    # !!! logger.addHandler(MaxLevelHandler())
    logger.info("Email обработчик инициализирован")


def run_test_scenarios() -> None:
    """Выполняет тестовые сценарии логирования"""
    logger.info("Система запущена")
    try:
        1 / 0
    except Exception as e:
        logger.error(f"Ошибка вычисления: {e}", exc_info=True)
    logger.warning("Ресурсы на исходе")
    logger.critical("Критическая ситуация!")
    logger.info("Команда *Stop* - отправка отчета")


def main() -> None:
    """Основная функция приложения"""
    try:
        setup_logging()
        configure_email_logging()
        run_test_scenarios()
    except Exception as e:
        logging.critical(f"Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
