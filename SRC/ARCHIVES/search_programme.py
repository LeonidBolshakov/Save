import subprocess
import string
import json
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class SearchProgramme:
    """Класс для локального поиска пути программы"""

    def __init__(self, config_file_path: str | None = None) -> None:
        """
        Инициализация объекта класса поиска архиватора.

        :param config_file_path: Путь к JSON-файлу конфигурации (опционально)
        """
        self.variables = EnvironmentVariables()
        self.config_file_path: str | None = config_file_path
        self.config: dict = {}

    def get_path(
            self, standard_program_paths: list[str] | str, programme_template: str
    ) -> str | None:
        """
        Основной метод получения пути к архиватору.

        :return: Найденный путь или None
        """

        # 1. Вывод пути из файла конфигуратора
        if path := self._programme_from_config_file(programme_template):
            return self._save_config(path, programme_template)

        # 2. Вывод пути из стандартных директорий сохранения программы
        if path := self._programme_from_common_paths(
                programme_template=programme_template,
                standard_program_paths=standard_program_paths,
        ):
            return self._save_config(path, programme_template)

        # 3. Проверка наличия программы в PATH
        if path := self._programme_in_system_path():
            return self._save_config(path, programme_template)

        # 4. Вывод пути в результате глобального поиска по всем дискам
        if path := self._programme_from_global_search(
                program_template=programme_template
        ):
            return self._save_config(path, programme_template)

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
                T.error_load_config.format(file_config=self.config_file_path, e=e)
            )
            return False

    def _programme_in_system_path(self) -> str | None:
        path = self.variables.get_var(C.ENV_PATTERN_PROGRAMME, C.PATTERN_PROGRAMME)
        if not self._test_programme_execution(path):
            logger.warning(T.error_run_system_path)
            return None
        return path

    def _programme_from_config_file(self, programme_template: str) -> str | None:
        """
        Возвращает путь на архиватор из конфига
        :param programme_template: - имя программы
        :return: Путь на программу или bkb None
        """
        logger.debug(T.search_in_config)
        if not self._setup_config_from_file():
            return None

        try:
            path = self.config[programme_template]
            if not self._test_programme_execution(path):
                logger.warning(
                    T.invalid_path_programme.format(path=f"{self.config_file_path}")
                )

                return None
            return path
        except KeyError:
            logger.warning(T.not_key_in_config)
            return None

    def _check_working_path(self, path: str | None) -> bool:
        """
        Проверяет работоспособность программы по указанному пути.

        :return:
            True - программа работоспособна,
            False - программа неработоспособна,
        """
        if not path or not Path(path).exists():
            return False
        if not self._test_programme_execution(path):
            return False
        return True

    @staticmethod
    def _test_programme_execution(path: str) -> bool:
        """Тестирует выполнение программы."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                test_archive = Path(tmpdir) / "test.exe"
                test_file = Path(tmpdir) / "test.txt"
                test_file.write_text("Test", encoding="utf-8")

                result = subprocess.run(
                    [path, "a", "-sfx", str(test_archive), str(test_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if result.returncode != 0:
                    logger.debug(
                        T.error_run_programme.format(path=path, e=result.stderr)
                    )
                return result.returncode == 0
            except FileNotFoundError:
                pass
            except Exception as e:
                logger.debug(T.error_run_programme_except.format(path=path, e=e))
                return False

    def _programme_from_common_paths(
            self, programme_template: str, standard_program_paths: list[str] | str
    ) -> str | None:

        if isinstance(standard_program_paths, str):
            standard_program_paths = [standard_program_paths]

        """Проверка стандартных путей установки программы"""
        logger.info(
            T.search_in_standard_paths.format(programme_template=programme_template)
        )
        for path in standard_program_paths:
            if self._check_working_path(path):
                return path
        logger.warning(T.search_in_standard_paths_failed)
        return None

    def _programme_from_global_search(self, program_template: str) -> str | None:
        """Поиск программы по всем доступным дискам."""
        logger.info(T.search_all_disks)
        for drive in self._get_available_drives():
            if path := self._global_search_in_disk(
                    path=str(drive), program_template=program_template
            ):
                return path
        return None

    @staticmethod
    def _get_available_drives() -> list[Path]:
        """Возвращает список доступных дисков."""
        return [
            Path(f"{d}:\\") for d in string.ascii_uppercase if Path(f"{d}:\\").exists()
        ]

    def _global_search_in_disk(self, path: str, program_template) -> str | None:
        """Рекурсивный поиск программы в указанном диске."""
        try:
            for item in Path(path).rglob(program_template):
                if self._check_working_path(str(item)):
                    return str(item)
        except PermissionError:
            logger.info(T.permission_error.format(path=path))

        return None

    def _save_config(self, path: str, programme_template: str) -> str:
        """
        Сохраняет путь к программе в конфигурационном файле и self.seven_zip_path."
        :param path: Полный путь к программе.
        :param programme_template: шаблон программы. Например - 7z.exe
        :return: Полный путь к программе
        """ ""
        self.seven_zip_path = path
        self.config[programme_template] = path

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
        seven_z_manager = SearchProgramme("../TEST/config.json")
    except ValueError:
        print(f"Путь к архиватору не найден")
    else:
        main_path = seven_z_manager.get_path(
            standard_program_paths=C.STANDARD_7Z_PATHS,
            programme_template=C.PATTERN_PROGRAMME,
        )
        print(
            main_path
            if main_path
            else f"Программа {C.PATTERN_PROGRAMME} не найдена. Установите программу"
        )


if __name__ == "__main__":
    main()
