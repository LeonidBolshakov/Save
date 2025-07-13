import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from seven_z_manager import SevenZManager
from arch_7z_spec import Arch7zSpec

LIST_FILE = r"C:\PycharmProjects\Save\list.txt"


class File7ZArchiving:
    def __init__(self):
        logger.debug("Инициализация FileArchiving")

        seven_z_manager = SevenZManager("file_config.txt")
        self.seven_z_path = seven_z_manager.get_7z_path()
        if not self.seven_z_path:
            error_msg = "На компьютере не найден архиватор 7z.exe. Надо установить"
            logger.critical(error_msg)
            raise OSError(error_msg)

    def make_local_archive(self, temp_dir: str) -> str:
        logger.debug("Начало создания и загрузки архива")
        try:
            local_path = Path(temp_dir, "archive.exe")
            local_path_str = str(local_path)
            logger.debug(f"Путь к архиву на локальном диске: {local_path_str}")

            arch_7z_spec = Arch7zSpec(
                arch_path=local_path_str,
                list_file=LIST_FILE,
                seven_zip_path=self.seven_z_path,
                password=os.getenv("PASSWORD_ARCHIVE", ""),
            )
            arch_7z_spec.make_archive()
            return local_path_str
        except Exception as e:
            error_msg = f"Ошибка при создании локального архива {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from None
