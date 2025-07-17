from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constant import Constant as C
from SRC.LOGGING.tunelogger import TuneLogger  # Для настройки системы логирования
from SRC.GENERAL.backupmanager import BackupManager


def load_and_validate_required_vars() -> None:
    """
    Загружает системные и пользовательские переменные окружения.
    Проверяет наличие и доступность обязательных переменных.
    Если какие-то переменные отсутствуют, генерируется исключение EnvironmentError.

    Raises:
        EnvironmentError: Если отсутствуют одна или несколько обязательных переменных
    """
    load_dotenv(dotenv_path=C.DOTENV_PATH)  # Загрузка переменных окружения

    missing = [var for var in C.REQUIRED_VARS if not os.getenv(var)]
    if missing:
        error_msg = (
            f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}"
        )
        logger.critical(error_msg)
        raise EnvironmentError(error_msg)


if __name__ == "__main__":
    """Точка входа в приложение резервного копирования.

    Выполняет:
    1. Настройку системы логирования
    2. Инициализацию менеджера резервного копирования
    3. Запуск основного процесса создания и загрузки резервных копий

    Логирует все этапы работы и обрабатывает возможные ошибки.
    """

    # Сбор из разных источников и проверка наличия необходимых переменных окружения
    load_and_validate_required_vars()

    # Настройка системы логирования
    customize_logger = TuneLogger()  # Создание экземпляра настройщика логов
    customize_logger.setup_logging()  # Применение настроек логирования

    logger.info("Запуск процесса резервного копирования")

    try:
        # Инициализация и запуск менеджера резервного копирования
        backup_manager = BackupManager()  # Создание экземпляра менеджера
        backup_manager.main()  # Запуск основного процесса

    except Exception as e:
        # Логирование необработанных исключений
        logger.critical(
            f"Критическая ошибка при выполнении резервного копирования: {str(e)}",
            exc_info=True,
        )
        raise  # Повторное возбуждение исключения для видимости в консоли
