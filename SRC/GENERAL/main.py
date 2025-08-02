import sys
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.backup_manager import BackupManager

if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""
    try:
        BackupManager().main()
        exit(0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        sys.exit(1)
