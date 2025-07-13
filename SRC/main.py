import sys
import logging
from dotenv import load_dotenv
import os
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)

from tunelogger import TuneLogger
from file7zarchiving import File7ZArchiving
from yandex_disk import YandexDisk
from maxlevelhandler import MaxLevelHandler


def validate_environment_vars():
    load_dotenv()

    REQUIRED_VARS = [
        "YANDEX_CLIENT_ID",
        "YANDEX_REDIRECT_URI",
        "YANDEX_SCOPE",
        "PASSWORD_ARCHIVE",
        "SENDER_EMAIL",
        "SENDER_PASSWORD",
        "RECIPIENT_EMAIL",
    ]
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
    if missing:
        error_msg = f"В ENV отсутствуют обязательные переменные: {', '.join(missing)}"
        logging.critical(error_msg)
        raise EnvironmentError(error_msg) from None


def write_file(local_path: str) -> str:
    yandex_disk = YandexDisk()
    logger.info("Начало загрузки на Яндекс.Диск")
    if not (_remote_path := yandex_disk.write_file_fast(local_path)):
        error_msg = "Не удалось записать архив на Яндекс-Диск"
        logger.error(error_msg)
        raise OSError(error_msg) from None
    else:
        logger.info(f"Архив успешно загружен на Яндекс.Диск по пути {_remote_path}")

    return _remote_path


def completion(failure: bool, remote_path: str | None) -> None:
    max_level = MaxLevelHandler().get_highest_level()
    name_max_level = logging.getLevelName(max_level)
    if failure:
        logger.info(f"{name_max_level.upper()}    --> Задание провалено.")
        logger.critical(
            f"***** Не менять! Информация для отправки служебного сообщения*Stop*"
        )
        sys.exit(1)
    else:
        match max_level:
            case logging.NOTSET | logging.DEBUG | logging.INFO:
                logger.info(f"     --> Задание успешно завершено.")
            case logging.WARNING:
                logger.warning(
                    f"{name_max_level}     --> Задание завершено с НЕ фатальными ошибками."
                )
            case logging.ERROR | logging.CRITICAL:
                logger.error(
                    f"{name_max_level}     --> Задание завершено с ФАТАЛЬНЫМИ ошибками уровня {logging.getLevelName(max_level).upper()}."
                )
        logger.critical(
            f"***** Не менять! Информация для отправки служебного сообщения*Stop* remote_path={remote_path}"
        )
        sys.exit(0)


def main():
    logger.info("Начало архивации и сохранения файлов в облако")
    with TemporaryDirectory() as temp_dir:
        try:
            validate_environment_vars()
            local_archive = File7ZArchiving()
            local_path = local_archive.make_local_archive(temp_dir)
            remote_path = write_file(local_path)
            completion(failure=False, remote_path=remote_path)
        except Exception:
            completion(failure=True, remote_path=None)


if __name__ == "__main__":
    customize_logger = TuneLogger()
    customize_logger.setup_logging()

    logger.info("Запуск приложения резервного копирования")

    main()
