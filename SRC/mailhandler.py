import logging
import time
from datetime import datetime
import sys
import os
import dotenv
from logging import LogRecord, Formatter, FileHandler, StreamHandler

import yagmail


class YagmailEmailHandler:
    """Обработчик для отправки уведомлений через email с помощью yagmail"""

    def __init__(self, sender_email: str, sender_password: str, recipient_email: str):
        if not sender_email or not sender_password or not recipient_email:
            raise ValueError("Отсутствуют учетные данные электронной почты")

        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_email(self, subject: str, content: str) -> bool:
        """Отправка сообщения через yagmail с обработкой ошибок"""
        try:
            # Для Яндекс-Почты
            yag = yagmail.SMTP(
                user=self.sender_email,
                password=self.sender_password,
                host="smtp.yandex.ru",
                port=465,
                smtp_ssl=True,
            )
            yag.send(to=self.recipient_email, subject=subject, contents=content)
            return True
        except yagmail.error.YagAddressError:
            logging.error("Ошибка в email адресе")
            return False
        except yagmail.error.YagInvalidEmailAddress:
            logging.error("Недопустимый email адрес")
            return False
        except Exception as e:
            logging.error(f"Ошибка отправки email: {str(e)}")
            return False


class MaxLevelEmailHandler(logging.Handler):
    """
    Кастомный обработчик логов, который отслеживает сообщение
    с максимальным уровнем и отправляет его при получении триггера
    """

    def __init__(self, email_handler: YagmailEmailHandler):
        """
        :param email_handler: Обработчик email
        """
        super().__init__()
        self.highest_level = 0
        self.email_handler = email_handler
        self.permanent_lock = False

    def emit(self, record: LogRecord):
        """Обработка входящего сообщения лога"""
        if self.permanent_lock:
            return

        # Проверяем триггер в сообщении
        if "*Stop*" in record.getMessage():
            self.permanent_lock = True
            self.send_archive_report(record)
        else:
            # Обновляем запись с максимальным уровнем
            if self.highest_level < record.levelno:
                self.highest_level = record.levelno

    def send_archive_report(self, record: LogRecord):
        """Отправка сообщения с максимальным уровнем"""
        subject, content = self._compose_email_content(self.highest_level, record)
        if not self._send_with_retry(subject, content):
            logging.error("Все попытки отправки email провалились")

        self.highest_level = 0  # Сброс состояния

    def _compose_email_content(
        self, highest_level: int, record: logging.LogRecord
    ) -> tuple[str, str]:
        """Формирует тему и содержание email на основе уровня лога"""
        # noinspection PyUnreachableCode
        match highest_level:
            case logging.DEBUG | logging.INFO:
                return self.text_mail_info(record)
            case logging.WARNING:
                return self.text_mail_info(record)
            case _:
                return self.text_mail_error_critical(
                    record, logging.getLevelName(highest_level)
                )

    def text_mail_info(self, record: LogRecord) -> tuple[str, str]:
        subject = (
            f"✅ Системное уведомление: Ежедневное сохранение данных прошло успешно"
        )
        message = record.getMessage()
        archive_path = ""
        if message.index("remote_path="):
            archive_path = message[
                message.index("remote_path=") + len("remote_path=") :
            ]
        content = (
            f"Сообщение: \n\n"
            f"Ежедневный архив Ваших файлов создан и успешно записан в облако.\n"
            f"Он расположен в облаке по адресу: {archive_path}\n"
            f"Время: {self.format_timestamp_russian(record.created)}"
        )
        return subject, content

    def text_mail_warning(self, record: LogRecord) -> tuple[str, str]:
        subject = f"⚠️ Системное уведомление: Предупреждение при архивации и сохранении данных в облако"
        message = record.getMessage()
        archive_path = ""
        if message.index("remote_path="):
            archive_path = message[
                message.index("remote_path=") + len("remote_path=") :
            ]
        content = (
            f"Сообщение: \n\n"
            f"Ежедневный архив Ваших файлов создан и успешно записан в облако.\n"
            f"Он расположен в облаке по адресу: {archive_path}\n"
            f"Однако есть предупреждения, которые необходимо посмотреть в LOG файле {self._get_log_path()}"
            f"Время: {self.format_timestamp_russian(record.created)}"
        )
        return subject, content

    def text_mail_error_critical(
        self, record: LogRecord, level_name: str
    ) -> tuple[str, str]:
        subject = "🚨 Системное уведомление: Ежедневное сохранение данных - Проблемы"
        content = (
            f"Сообщение: Архивация и запись архива в облако провалились.\n\n"
            f"Максимальный уровень ошибки: {level_name} ({record.levelno})\n"
            f"Подробности в LOG файле: {self._get_log_path()}\n"
            f"Время: {self.format_timestamp_russian(record.created)}"
        )

        return subject, content

    @staticmethod
    def _get_log_path() -> str | None:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                return handler.baseFilename
        return None

    def _send_with_retry(
        self, subject: str, content: str, max_attempts: int = 3
    ) -> bool:
        """Выполняет отправку email с повторными попытками"""
        attempts = 0
        while attempts < max_attempts:
            try:
                error_msg = ""
                if self.email_handler.send_email(subject, content):
                    return True
            except Exception as e:
                error_msg = str(e)
            logging.error(
                f"Ошибка при отправке email (попытка {attempts + 1}): {error_msg}",
                exc_info=True,
            )

            attempts += 1
            if attempts < max_attempts:
                time.sleep(5)

        return False

    @staticmethod
    def format_timestamp_russian(timestamp: float) -> str:
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

        dt = datetime.fromtimestamp(timestamp)
        day = dt.day
        month = MONTHS_RU[dt.month]
        year = dt.year
        time_str = dt.strftime("%H:%M")
        return f"{day} {month} {year} года {time_str}"


def setup_logging(log_file: str = "application.log"):
    """Явная настройка системы логирования с записью в файл"""
    # Создаем форматтер
    formatter = Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Консольный обработчик (stdout)
    console_handler = StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Файловый обработчик
    file_handler = FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Удаляем стандартные обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Добавляем наши обработчики
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Возвращаем настроенный логгер
    return root_logger


def get_email_details():
    """Безопасное получение учетных данных для email"""
    # 1. Проверка переменных окружения

    dotenv.load_dotenv()
    sender_email = os.getenv("SENDER_EMAIL", "")
    sender_password = os.getenv("SENDER_PASSWORD", "")
    recipient_email = os.getenv("RECIPIENT_EMAIL", "")

    # 2. Проверка наличия учетных данных
    if not sender_email or not sender_password:
        logging.critical("Email учетные данные не найдены!")
        logging.critical("Установите переменные окружения:")
        logging.critical("SENDER_EMAIL и SENDER_PASSWORD")
        sys.exit(1)

    return sender_email, sender_password, recipient_email


def main():
    """Основная функция приложения"""
    try:
        # 1. Настройка логирования
        setup_logging()
        app_logger = logging.getLogger("app")
        app_logger.info("Система логирования инициализирована")

        # 2. Получение учетных данных для email
        sender_email, sender_password, recipient_email = get_email_details()
        app_logger.info(f"Учетные данные email получены. Получатель: {recipient_email}")

        # 3. Инициализация обработчиков
        email_handler = YagmailEmailHandler(
            sender_email, sender_password, recipient_email
        )

        email_log_handler = MaxLevelEmailHandler(email_handler)
        email_log_handler.setLevel(logging.DEBUG)

        # Добавляем обработчик к логгеру приложения
        app_logger.addHandler(email_log_handler)
        app_logger.info("Обработчики логов инициализированы")

        # 4. Тестовые сообщения
        app_logger.info("Информационное сообщение: система запущена")

        # Имитация различных сценариев
        try:
            # Генерируем исключение для теста
            1 / 0
        except Exception as e:
            app_logger.error("Ошибка вычисления: %s", str(e), exc_info=True)

        app_logger.warning("Предупреждение: ресурсы на исходе")
        app_logger.critical("КРИТИЧЕСКАЯ СИТУАЦИЯ: система на грани сбоя!")

        # Триггерное сообщение
        app_logger.info("Пользователь ввел команду *Stop* - отправляем email")

    except Exception as e:
        logging.critical(f"Фатальная ошибка в приложении: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Запуск основного приложения
    main()
