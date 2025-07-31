import sys
import logging

logger = logging.getLogger(__name__)

from backupmanager import BackupManager

if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""
    try:
        BackupManager().main()
        exit(0)
    except Exception:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
