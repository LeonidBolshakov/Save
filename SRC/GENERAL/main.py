import time
import sys
import logging

logger = logging.getLogger(__name__)

from SRC.LOGGING.tunelogger import TuneLogger  # Для настройки системы логирования
from SRC.GENERAL.backupmanager import BackupManager
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constant import Constant as C
from SRC.GENERAL.textmessage import TextMessage as T


def validate_vars_environments():
    logging.basicConfig(
        level=logging.INFO,
        format=C.LOG_FORMAT,
    )  # Настройка логирования только для выполнения следующего вызова

    EnvironmentVariables().validate_vars()  # Проверка наличия переменных окружения

    for (
        handler
    ) in logging.root.handlers:  # Отказ от предыдущей настройки на логирование
        logging.root.removeHandler(handler)


def main():
    """
    Выполняет:
    1. Настройку системы логирования
    2. Инициализацию менеджера резервного копирования
    3. Запуск основного процесса создания и загрузки резервных копий

    Логирует все этапы работы и обрабатывает возможные ошибки.
    """
    validate_vars_environments()  # Проверка наличия переменных окружения
    TuneLogger().setup_logging()  # Настройка системы логирования

    logger.info(T.start_main)
    start_time = time.time()

    try:
        BackupManager().main()  # Запуск основного процесса
    except KeyboardInterrupt:
        logger.error(T.canceled_by_user)
        raise
    except SystemExit:
        logger.info(T.successful)
    except Exception as e:
        logger.exception(T.critical_error_type.format(type=e.__class__.__name__, e=e))
        raise  # Повторное возбуждение исключения для видимости в консоли
    finally:
        logger.info(T.time_run.format(time=f"{time.time() - start_time:.2f}"))


if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""
    try:
        main()
    except Exception:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
