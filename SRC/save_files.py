import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from tempfile import TemporaryDirectory
import os
import sys
from pathlib import Path

from TEST.test_arch_7z_spec import local_archive_path
from seven_z_manager import SevenZManager
from arch_7z_spec import Arch7zSpec
from yandex_disk import YandexDisk
import mailhandler

LIST_FILE = r"C:\PycharmProjects\Save\list.txt"

# Настройка логгера для модуля
logger = logging.getLogger(__name__)


class SaveFiles:
    def __init__(self):
        logger.info("Инициализация SaveFiles")

        seven_z_manager = SevenZManager("file_config.txt")
        self.seven_z_path = seven_z_manager.get_7z_path()
        if not self.seven_z_path:
            message = "На компьютере не найден архиватор 7z.exe. Надо установить"
            logger.critical(message)
            raise OSError(message)

        self._validate_environment_vars()

    @staticmethod
    def _validate_environment_vars():
        load_dotenv()

        REQUIRED_VARS = [
            "YANDEX_CLIENT_ID",
            "YANDEX_REDIRECT_URI",
            "YANDEX_SCOPE",
            "PASSWORD",
            "SENDER_EMAIL",
            "SENDER_PASSWORD",
            "RECIPIENT_EMAIL",
        ]
        missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
        if missing:
            message = f"В ENV отсутствуют обязательные переменные: {', '.join(missing)}"
            logging.error(message)
            raise EnvironmentError(message) from None

    def make_and_write_archive(self) -> str:
        logger.info("Начало создания и загрузки архива")
        try:
            with TemporaryDirectory() as tmp_dir:
                local_path = self._make_archive(tmp_dir)
                print(1)
                return self.upload_to_yandex_disk(local_path)
        except Exception as ex:
            message = f"Ошибка в make_and_write_archive {ex}"
            logger.error(message)
            raise RuntimeError(message) from ex

    def _make_archive(self, tmp_dir: str) -> str:
        local_path = str(Path(tmp_dir) / "archive.exe")
        logger.debug(f"Временный путь к архиву: {local_path}")

        arch_7z_spec = Arch7zSpec(
            arch_path=local_path,
            list_file=LIST_FILE,
            seven_zip_path=self.seven_z_path,
            password=os.getenv("PASSWORD", ""),
        )

        if arch_7z_spec.make_archive():
            logger.info("Архив успешно создан")
            return local_path
        else:
            message = "Не удалось создать архив"
            logger.critical(message)
            raise OSError(message) from None

    @staticmethod
    def upload_to_yandex_disk(local_archive_path: str) -> str:
        yandex_disk = YandexDisk()
        logger.info("Начало загрузки на Яндекс.Диск")

        if not (remote_path := yandex_disk.write_archive_fast(local_archive_path)):
            message = "Не удалось записать архив на Яндекс-Диск"
            logger.critical(message)
            raise OSError(message) from None
        else:
            logger.info(f"Архив успешно загружен на Яндекс.Диск по пути {remote_path}")
            return remote_path


def setup_logging():
    """Настройка глобального логирования"""
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )
    log_level = get_log_level()
    configure_handlers(log_format, log_level)

    # Для библиотек устанавливаем более высокий уровень
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yadisk").setLevel(logging.WARNING)


def get_log_level() -> int:
    """
    Определение уровня логирования
    :return: (int) - Уровень логирования
    """
    LOG_LEVELS: dict[str, int] = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    load_dotenv()
    log_level_name = os.getenv("LOGGING_LEVEL", "info").lower()
    log_level = LOG_LEVELS.get(log_level_name, logging.INFO)
    logger.debug(f"Уровень логирования установлен в {log_level_name}")
    return log_level


def create_handler_rotation() -> logging.handlers.RotatingFileHandler:
    return RotatingFileHandler(
        filename="backup.log",
        maxBytes=1 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
        delay=True,
    )


def create_email_handler():
    load_dotenv()
    sender_email = os.getenv("SENDER_EMAIL", "")
    sender_password = os.getenv("SENDER_PASSWORD", "")
    recipient_email = os.getenv("RECIPIENT_EMAIL", "")

    return mailhandler.YagmailEmailHandler(
        sender_email, sender_password, recipient_email
    )


def configure_handlers(log_format: str, log_level: int) -> None:
    email_handler = create_email_handler()

    file_log_handler = create_handler_rotation()
    email_log_handler = mailhandler.MaxLevelEmailHandler(email_handler)
    console_log_handler = logging.StreamHandler(sys.stdout)
    log_handers = [file_log_handler, email_log_handler, console_log_handler]
    # Настройка обработчиков
    for log_handler in log_handers:
        log_handler.setFormatter(logging.Formatter(log_format))
        log_handler.setLevel("DEBUG" if log_handler == email_log_handler else log_level)

    configure_root_handlers(log_handers)


def configure_root_handlers(log_handers: list[logging.Handler]) -> None:
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel("DEBUG")
    for log_handler in log_handers:
        root_logger.addHandler(log_handler)


if __name__ == "__main__":
    setup_logging()
    main_logger = logging.getLogger()
    main_logger.info("Запуск приложения резервного копирования")

    try:
        save_files = SaveFiles()
        _remote_path = save_files.make_and_write_archive()
        main_logger.critical(
            f"***** Не менять! Информация для отправки служебного сообщения*Stop* remote_path={_remote_path}"
        )
        sys.exit(0)
    except Exception as e:
        main_logger.critical(
            f"* Не менять! Информация для отправки служебного сообщения*Stop*{e}"
        )
        sys.exit(1)
