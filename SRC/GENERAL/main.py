import sys
import logging

from SRC.GENERAL.backupmanager import BackupManager

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""
    try:
        backup_manager = BackupManager()
        backup_manager.main()
    except Exception:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
