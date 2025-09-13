import sys
import logging

from SRC.GENERAL.backup_manager_7z import BackupManager7z

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""
    try:
        BackupManager7z().main()
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Необработанная ошибка {e}")
        sys.exit(1)
