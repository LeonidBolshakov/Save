import subprocess
import string
import json
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class Search7zExe:
    """Класс для локального поиска утилиты архивации 7z.exe."""

    def __init__(self, config_file_path: str | None = None):
        """
        Инициализация менеджера 7z.

        :param config_file_path: Путь к JSON-файлу конфигурации (опционально)
        """
        self.config_file_path: str | None = config_file_path
        self.default_7z_paths: list[str] = C.DEFAULT_7Z_PATHS
        self.pattern_7_z = C.PATTERN_7_Z
        self.config: dict = {}

    def get_path(self) -> str | None:
        """
        Основной метод получения пути к 7z.exe.

        :return: Найденный путь или None
        """

        # 1. Вывод пути из файла конфигуратора
        if path := self._7z_from_config_file():
            return self._save_config(path)

        # 2. Вывод пути из типичных директорий сохранения программы
        if path := self._7z_from_common_paths():
            return self._save_config(path)

        # 3. Вывод пути в результате глобального поиска по всем дискам
        if path := self._7z_from_global_search():
            return self._save_config(path)

        # Программа не найдена
        return None

    def _setup_config_from_file(self) -> bool:
        """Загружает JSON-конфигурацию."""
        if not (self.config_file_path and Path(self.config_file_path).exists()):
            logger.warning(
                T.not_found_config_file.format(config_file_path=self.config_file_path)
            )
            return False
        try:
            with open(self.config_file_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
                return True
        except Exception as e:
            logger.warning(
                T.error_load_7z.format(file_config=self.config_file_path, e=e)
            )
            return False

    def _7z_from_config_file(self) -> str | None:
        """Возвращает путь на архиватор из конфига"""
        if not self._setup_config_from_file():
            return None

        try:
            path = self.config[C.CONFIG_KEY_SEVEN_ZIP_PATH]
            if not self._check_working_path(path):
                logger.warning(
                    T.invalid_path_7z.format(path=f"{self.config_file_path}")
                )

                return None
            return path
        except KeyError:
            logger.warning(T.not_key_in_config)
            return None

    @staticmethod
    def _check_working_path(path: str) -> bool:
        """
        Проверяет работоспособность 7z.exe по указанному пути.

        :return:
            True - программа работоспособна,
            False - программа неработоспособна,
        """
        if not path or not Path(path).exists():
            return False
        if not Search7zExe._test_7z_execution(path):
            return False
        return True

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
                if result.returncode != 0:
                    logger.debug(T.error_run_7z.format(path=path, e=result.stderr))
                return result.returncode == 0
            except Exception as e:
                logger.debug(T.error_run_7z_except.format(path=path, e=e))
                return False

    def _7z_from_common_paths(self) -> str | None:
        """Проверка стандартных путей установки 7-Zip."""
        logger.info(T.search_in_standard_paths.format(pattern_7_z=self.pattern_7_z))
        for path in self.default_7z_paths:
            if self._check_working_path(path):
                return path
        logger.warning(T.search_in_standard_paths_failed)
        return None

    def _7z_from_global_search(self) -> str | None:
        """Поиск 7z.exe по всем доступным дискам."""
        logger.info(T.search_all_disks.format(pattern_7_z=self.pattern_7_z))
        for drive in self._get_available_drives():
            if path := self._global_search_in_disk(str(drive)):
                return path
        return None

    @staticmethod
    def _get_available_drives() -> list[Path]:
        """Возвращает список доступных дисков."""
        return [
            Path(f"{d}:\\") for d in string.ascii_uppercase if Path(f"{d}:\\").exists()
        ]

    def _global_search_in_disk(self, path: str) -> str | None:
        """Рекурсивный поиск 7z.exe в указанном диске."""
        try:
            for item in Path(path).rglob(self.pattern_7_z):
                if self._check_working_path(str(item)):
                    return str(item)
        except PermissionError:
            logger.info(T.permission_error.format(path=path))

        return None

    def _save_config(self, path: str) -> None:
        """Сохраняет путь к 7z в конфигурацию."""
        str_path = str(path)
        self.seven_zip_path = str_path
        self.config[C.CONFIG_KEY_SEVEN_ZIP_PATH] = str_path

        if self.config_file_path:
            try:
                with open(self.config_file_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(T.error_saving_config.format(e=e))

        logger.debug(T.program_is_localed.format(path=path))
        return path


def main():
    try:
        seven_z_manager = Search7zExe("../TEST/config.json")
    except ValueError:
        print(f"Путь к архиватору не найден")
    else:
        main_path = seven_z_manager.get_path()
        print(
            main_path
            if main_path
            else f"Программа {seven_z_manager.pattern_7_z} не найдена. Установите программу"
        )


if __name__ == "__main__":
    main()
