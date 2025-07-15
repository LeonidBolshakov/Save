import subprocess
import string
import json
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)

from constant import Constant as C


class SevenZManager:
    """Класс для управления доступом к утилите архивации 7z.exe."""

    def __init__(self, file_config: str | None = None):
        """
        Инициализация менеджера 7z.

        :param file_config: Путь к JSON-файлу конфигурации (опционально)
        """
        self.seven_zip_path: str | None = None
        self.file_config: str | None = file_config
        self.default_7z_paths: list[str] = C.DEFAULT_7Z_PATHS
        self.pattern_7_z = C.PATTERN_7_Z
        self.config: dict = {}
        self._init_config()

    def _init_config(self) -> None:
        """Загрузка и проверка конфигурации из файла."""
        if not self.file_config or not Path(self.file_config).exists():
            return

        self._load_config()
        self._validate_config_path()

    def _load_config(self) -> None:
        """Загружает JSON-конфигурацию."""
        if not self.file_config or not Path(self.file_config).exists():
            logger.warning(
                f"Файл с путём на 7z не задан или не существует {self.file_config}"
            )
            return
        try:
            with open(self.file_config, "r", encoding="utf-8") as f:
                self.config = json.load(f)
        except Exception as e:
            logger.warning(
                f"Ошибка загрузки файла с путём на 7z {self.file_config}: {e}"
            )
            return

    def _validate_config_path(self) -> None:
        """Проверяет путь из конфига на валидность."""
        try:
            path = self.config["SEVEN_ZIP_PATH"]
            match self._check_working_path(path):
                case 0:
                    self.seven_zip_path = path
                case _:
                    error_msg = f"Некорректный путь к 7z.exe в конфиге: {path}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        except KeyError:
            logger.warning('В конфиге нет ключа "SEVEN_ZIP_PATH"')

    @staticmethod
    def _check_working_path(path: str) -> int:
        """
        Проверяет работоспособность 7z.exe по указанному пути.

        :return:
            0 - программа работоспособна,
            1 - программа неработоспособна,
            2 - файл не существует
        """
        if not path or not Path(path).exists():
            return 2
        if not SevenZManager._test_7z_execution(path):
            return 1
        return 0

    @staticmethod
    def _test_7z_execution(path: str) -> bool:
        """Тестирует выполнение 7z.exe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_archive = Path(tmpdir) / "test.exe"
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test", encoding="utf-8")

            try:
                result = subprocess.run(
                    [path, "a", "-sfx", str(test_archive), str(test_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                return result.returncode == 0
            except Exception:
                return False

    def get_7z_path(self) -> str | None:
        """
        Основной метод получения пути к 7z.exe.

        :return: Найденный путь или None
        """
        if self.seven_zip_path:
            return self.seven_zip_path

        if path := self._check_common_paths():
            self._save_config(path)
            return path

        if path := self._global_search():
            self._save_config(path)
            return path

        return None

    def _check_common_paths(self) -> str | None:
        """Проверка стандартных путей установки 7-Zip."""
        for path in self.default_7z_paths:
            if self._check_working_path(path) == 0:
                return path
        return None

    def _global_search(self) -> str | None:
        """Поиск 7z.exe по всем доступным дискам."""
        logger.info(f"Поиск {self.pattern_7_z} по всем дискам...")
        for drive in self._get_available_drives():
            if path := self._global_search_in_disk(str(drive)):
                return path
        return None

    def _global_search_in_disk(self, path: str) -> str | None:
        """Рекурсивный поиск 7z.exe в указанном диске."""
        try:
            for item in Path(path).rglob(self.pattern_7_z):
                if self._check_working_path(str(item)) == 0:
                    return str(item)
        except PermissionError:
            logger.debug(f"Нет доступа к {path}")
        return None

    def _save_config(self, path: Path | str) -> None:
        """Сохраняет путь к 7z в конфигурацию."""
        str_path = str(path)
        self.seven_zip_path = str_path
        self.config["SEVEN_ZIP_PATH"] = str_path

        if self.file_config:
            try:
                with open(self.file_config, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(f"Ошибка сохранения конфига: {e}")

    @staticmethod
    def _get_available_drives() -> list[Path]:
        """Возвращает список доступных дисков."""
        return [
            Path(f"{d}:\\") for d in string.ascii_uppercase if Path(f"{d}:\\").exists()
        ]


def main():
    try:
        seven_z_manager = SevenZManager("../TEST/config.json")
    except ValueError:
        print(f"Путь к архиватору не найден")
    else:
        main_path = seven_z_manager.get_7z_path()
        print(
            main_path
            if main_path
            else f"Программа {seven_z_manager.pattern_7_z} не найдена. Установите программу"
        )


if __name__ == "__main__":
    main()
