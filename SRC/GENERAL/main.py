import logging

logger = logging.getLogger(__name__)

from SRC.LOGGING.tunelogger import TuneLogger  # Для настройки системы логирования
from SRC.GENERAL.backupmanager import BackupManager

if __name__ == "__main__":
    """Точка входа в приложение резервного копирования.

    Выполняет:
    1. Настройку системы логирования
    2. Инициализацию менеджера резервного копирования
    3. Запуск основного процесса создания и загрузки резервных копий

    Логирует все этапы работы и обрабатывает возможные ошибки.
    """

    # Настройка системы логирования
    customize_logger = TuneLogger()  # Создание экземпляра настройщика логов
    customize_logger.setup_logging()  # Применение настроек логирования

    logger.info("Запуск процесса резервного копирования")
    try:
        backup_manager = BackupManager()  # Создание экземпляра менеджера
        backup_manager.main()  # Запуск основного процесса
    except Exception as e:
        # Логирование необработанных исключений
        logger.critical(
            f"Критическая ошибка при выполнении резервного копирования: {str(e)}",
            exc_info=True,
        )
        raise  # Повторное возбуждение исключения для видимости в консоли
