import logging

logger = logging.getLogger(__name__)

from SRC.LOGGING.tunelogger import TuneLogger  # Для настройки системы логирования
from SRC.GENERAL.backupmanager import BackupManager
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constant import Constant as C


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

    logger.info("Запуск процесса резервного копирования")
    try:
        BackupManager().main()  # Запуск основного процесса
    except Exception as e:
        # Логирование исключений
        logger.exception(e)
        raise  # Повторное возбуждение исключения для видимости в консоли


if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""

    main()
