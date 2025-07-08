import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from tempfile import TemporaryDirectory
import os
import sys
from pathlib import Path

from seven_z_manager import SevenZManager
from arch_7z_spec import Arch7zSpec
from yandex_disk import YandexDisk

LIST_FILE = r"C:\PycharmProjects\Save\list.txt"

# Настройка логгера для модуля
logger = logging.getLogger(__name__)


class SaveFiles:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Инициализация SaveFiles")

        seven_z_manager = SevenZManager("file_config.txt")
        self.seven_z_path = seven_z_manager.get_7z_path()
        if not self.seven_z_path:
            self.logger.critical("7z.exe не найден! Установите архиватор")
            raise OSError("На компьютере не найден архиватор 7z.exe. Надо установить")

        self.validate_environment_vars()

    @staticmethod
    def validate_environment_vars():
        load_dotenv()

        required_vars = [
            "YANDEX_CLIENT_ID",
            "YANDEX_REDIRECT_URI",
            "YANDEX_SCOPE",
            "PASSWORD",
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            logging.error(f"Отсутствуют ENV переменные: {', '.join(missing)}")
            raise EnvironmentError(
                f"Отсутствуют обязательные ENV переменные: {', '.join(missing)}"
            ) from None

    def make_and_write_archive(self):
        self.logger.info("Начало создания и загрузки архива")
        try:
            with TemporaryDirectory() as tmp_dir:
                archive_path = self.create_archive(tmp_dir)
                self.upload_to_yandex_disk(archive_path)
        except Exception as ex:
            self.logger.exception(f"Критическая ошибка в make_and_write_archive {ex}")
            raise

    def create_archive(self, tmp_dir: str) -> str:
        archive_path = str(Path(tmp_dir) / "archive.exe")
        self.logger.debug(f"Временный путь к архиву: {archive_path}")

        arch_7z_spec = Arch7zSpec(
            arch_path=archive_path,
            list_file=LIST_FILE,
            seven_zip_path=self.seven_z_path,
            password=os.getenv("PASSWORD", ""),
        )

        if not arch_7z_spec.make_archive():
            self.logger.error("Ошибка создания архива")
            raise OSError("Не удалось создать архив") from None
        else:
            self.logger.info("Архив успешно создан")
            return archive_path

    def upload_to_yandex_disk(self, archive_path: str):
        yandex_disk = YandexDisk()
        self.logger.info("Начало загрузки на Яндекс.Диск")

        if not yandex_disk.write_archive_fast(archive_path):
            self.logger.error("Ошибка загрузки на Яндекс.Диск")
            raise OSError("Не удалось записать архив на Яндекс. Диск") from None
        else:
            self.logger.info("Архив успешно загружен на Яндекс.Диск")


def setup_logging():
    """Настройка глобального логирования"""
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )
    log_level = get_log_level()
    file_handler = create_handler_rotation(log_format, log_level)
    configure_handlers(log_format, log_level, file_handler)

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

    log_level_name = os.getenv("LOGGING_LEVEL", "info").lower()
    log_level = LOG_LEVELS.get(log_level_name, logging.INFO)
    logger.debug(f"Уровень логирования установлен в {log_level_name}")
    return log_level


def create_handler_rotation(
        log_format: str, log_level: int
) -> logging.handlers.RotatingFileHandler:
    """Создать обработчик с ротацией"""
    file_handler = RotatingFileHandler(
        filename="backup.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    file_handler.setLevel(logging.getLevelName(log_level))

    return file_handler


def configure_handlers(
        log_format: str, log_level: int, file_handler: logging.handlers.RotatingFileHandler
) -> None:
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format))
    console_handler.setLevel(log_level)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


if __name__ == "__main__":
    setup_logging()
    main_logger = logging.getLogger("main")
    main_logger.info("Запуск приложения резервного копирования")

    try:
        save_files = SaveFiles()
        save_files.make_and_write_archive()
        main_logger.info("Процесс завершен успешно")
        sys.exit(0)
    except Exception as e:
        main_logger.exception(
            "Критическая ошибка при формировании или записи архива в облако"
        )
        sys.exit(1)
