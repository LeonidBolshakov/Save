import string
import json
from pathlib import Path
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.textmessage import TextMessage as T


class SearchProgramme(ABC):
    """Класс для локального поиска пути программы"""

    def __init__(self) -> None:
        """Инициализация объекта класса поиска архиватора"""
        # self.variables = EnvironmentVariables()
        self.config_path: dict = {}

    @abstractmethod
    def _test_programme_execution(self, path: str) -> bool:
        pass

    def get_path(
        self,
        config_file_path: str,
        standard_program_paths: list[str] | str | None,
        programme_template: str,
    ) -> str | None:
        """
        Основной метод получения пути к архиватору.

        :param config_file_path: Путь к JSON-файлу конфигурации (опционально)
        :param standard_program_paths: Список стандартных путей на программу
        :param programme_template: шаблон имени программы
        :return: Найденный путь или None
        """

        # 1. Вывод пути из файла конфигуратора
        if path := self._programme_from_config_file(
            programme_template, config_file_path
        ):
            return self._save_config(path, programme_template, config_file_path)

        # 2. Вывод пути из стандартных директорий сохранения программы
        if path := self._programme_from_common_paths(
            programme_template=programme_template,
            standard_program_paths=standard_program_paths,
        ):
            return self._save_config(path, programme_template, config_file_path)

        # 3. Проверка наличия программы в PATH
        if path := self._programme_in_system_path(programme_template):
            return self._save_config(path, programme_template, config_file_path)

        # 4. Вывод пути в результате глобального поиска по всем дискам
        if path := self._programme_from_global_search(
            program_template=programme_template
        ):
            return self._save_config(path, programme_template, config_file_path)

        # Программа не найдена
        return None

    def _setup_config_from_file(self, config_file_path: str) -> bool:
        """Загружает JSON-конфигурацию."""
        if not (config_file_path and Path(config_file_path).exists()):
            logger.warning(
                T.not_found_config_file.format(config_file_path=config_file_path)
            )
            return False
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                self.config_path = json.load(f)
                return True
        except Exception as e:
            logger.warning(
                T.error_load_config.format(file_config=config_file_path, e=e)
            )
            return False

    def _programme_in_system_path(self, programme_template: str) -> str | None:
        if not self._test_programme_execution(programme_template):
            logger.warning(T.error_run_system_path)
            return None
        return programme_template

    def _programme_from_config_file(
        self, programme_template: str, config_file_path: str
    ) -> str | None:
        """
        Возвращает путь на архиватор из конфига
        :param programme_template: - имя программы
        :param config_file_path: Путь на файл конфигурации, содержащий путь на исполняемую программу

        :return: Путь на программу или None
        """
        logger.debug(T.search_in_config)
        if not self._setup_config_from_file(config_file_path):
            return None

        try:
            path = self.config_path[programme_template]
            if not self._test_programme_execution(path):
                logger.warning(
                    T.invalid_path_programme.format(path=f"{config_file_path}")
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

    def _programme_from_common_paths(
        self, programme_template: str, standard_program_paths: list[str] | str | None
    ) -> str | None:

        if not standard_program_paths:
            return None

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

    def _save_config(
        self, path: str, programme_template: str, config_file_path: str
    ) -> str:
        """
        Сохраняет путь к программе в конфигурационном файле и self.program_path."
        :param path: Полный путь к программе.
        :param programme_template: шаблон программы. Например - 7z.exe
        :return: Полный путь к программе
        """ ""
        self.program_path = path
        self.config_path[programme_template] = path

        if config_file_path:
            try:
                with open(config_file_path, "w", encoding="utf-8") as f:
                    json.dump(self.config_path, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(T.error_saving_config.format(e=e))

        logger.debug(T.program_is_localed.format(path=path))
        return path
