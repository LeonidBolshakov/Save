import sys
import logging

from SRC.GENERAL.backup_manager_7z import BackupManager7z
from SRC.GENERAL.paths_win import prepare_files

logger = logging.getLogger(__name__)


def main() -> int:
    """Точка входа в приложение резервного копирования."""

    # подготовка env
    env_path = prepare_files()

    try:
        manager = BackupManager7z()
        manager.main()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        logger.exception(f"Необработанная ошибка {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
