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
        self.config_path: dict = {}

    @abstractmethod
    def test_programme_execution(self, path: str) -> bool:
        """
        Тест искомой программы.

        Программа должна выполнить передаваемую в параметре программу на минимальных данных.
        Если программа выполниться без прерываний и вернёт код возврата 0 или ожидаемый результат,
        то всё ОК.

        Пример программы для архиватора 7z.exe в файле SRC/ARCHIVES/search_programme.py

        :param path: (str) Полный путь на выполняемую программу.

        :return:True, если всё ОК, иначе False
        """
        pass

    def get_path(
        self,
        config_file_path: str,
        standard_program_paths: list[str] | str | None,
        programme_full_name: str,
    ) -> str | None:
        """
        Основной метод получения пути к архиватору.

        :param config_file_path:    Путь к JSON-файлу конфигурации,
                                    содержащему путь на выполняемую программу (опционально)
        :param standard_program_paths: Список стандартных путей на программу или стандартный путь на программу
        :param programme_full_name: имя программы с расширением

        :return: Найденный путь или None
        """

        # 1. Вывод пути из файла конфигуратора
        if path := self._programme_from_config_file(
            programme_full_name, config_file_path
        ):
            return self._save_config(path, programme_full_name, config_file_path)

        # 2. Вывод пути из стандартных директорий сохранения программы
        if path := self._programme_from_standard_paths(
            programme_full_name=programme_full_name,
            standard_program_paths=standard_program_paths,
        ):
            return self._save_config(path, programme_full_name, config_file_path)

        # 3. Проверка наличия программы в PATH
        if self._programme_in_system_path(programme_full_name):
            return self._save_config(
                programme_full_name, programme_full_name, config_file_path
            )

        # 4. Вывод пути в результате глобального поиска по всем дискам
        if path := self._programme_from_global_search(
            programme_full_name=programme_full_name
        ):
            return self._save_config(path, programme_full_name, config_file_path)

        # Программа не найдена
        return None

    def _setup_config_from_file(self, config_file_path: str | None) -> bool:
        """
        Загружает JSON-конфигурацию, содержащую путь на исполняемый файл

        :param config_file_path: Полный путь на файл с JSON конфигурацией

        :return: True, если JSON конфигурация загружена, FALSE в противном случае
        """
        if not (config_file_path and Path(config_file_path).exists()):
            logger.info(
                T.not_found_config_file.format(config_file_path=config_file_path)
            )
            return False
        try:
            with open(config_file_path, "r", encoding="utf-8") as f:
                self.config_path = json.load(f)
                return True
        except Exception as e:
            logger.info(
                T.error_load_config.format(config_file_path=config_file_path, e=e)
            )
            return False

    def _programme_in_system_path(self, programme_full_name: str) -> bool:
        """
        Проверка программы в системных путях, указанных в PATH

        :param programme_full_name: Полное имя программы с расширением

        :return:    True, если программа находится в системных путях,
                    None если программа не находится в системных путях.
        """
        if not self.test_programme_execution(programme_full_name):
            logger.debug(T.error_run_system_path)
            return False
        return True

    def _programme_from_config_file(
        self, programme_full_name: str, config_file_path: str
    ) -> str | None:
        """
        Возвращает путь на архиватор из конфигурационного файла

        :param programme_full_name: - имя программы, включая расширение
        :param config_file_path: Путь на файл конфигурации, содержащий путь на исполняемую программу

        :return: Путь на программу или None
        """
        logger.debug(T.search_in_config)
        if not self._setup_config_from_file(config_file_path):
            return None

        try:
            path = self.config_path[programme_full_name]
            if not self.test_programme_execution(path):
                logger.debug(
                    T.invalid_path_programme.format(path=f"{config_file_path}")
                )
                return None
            return path
        except KeyError:
            logger.warning(T.not_key_in_config.format(key=programme_full_name))
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
        if not self.test_programme_execution(path):
            return False

        return True

    def _programme_from_standard_paths(
        self, programme_full_name: str, standard_program_paths: list[str] | str | None
    ) -> str | None:
        """
        проверка наличия программы по стандартным, для программы, путям

        :param programme_full_name: Полное имя программы, включая расширение
        :param standard_program_paths: стандартный путь для программы или список стандартных путей

        :return: Путь на работающую программу или None
        """
        if not standard_program_paths:
            return None

        if isinstance(standard_program_paths, str):
            standard_program_paths = [standard_program_paths]

        logger.info(
            T.search_in_standard_paths.format(programme_full_name=programme_full_name)
        )
        for path in standard_program_paths:
            if self._check_working_path(path):
                return path
        logger.warning(T.search_in_standard_paths_failed)
        return None

    def _programme_from_global_search(self, programme_full_name: str) -> str | None:
        """
        Поиск программы по всем доступным дискам.

        :param programme_full_name: Полное имя программы, включая расширение

        :return: Путь на программу или None
        """
        logger.info(T.search_all_disks)
        for drive in self._get_available_drives():
            if path := self._global_search_in_disk(
                path=str(drive), program_full_name=programme_full_name
            ):
                return path
        return None

    @staticmethod
    def _get_available_drives() -> list[Path]:
        """
        Возвращает список доступных дисков

        :return: Список доступных дисков в формате строк ["C:\", "D:\"]
        """
        return [
            Path(f"{d}:\\") for d in string.ascii_uppercase if Path(f"{d}:\\").exists()
        ]

    def _global_search_in_disk(self, path: str, program_full_name) -> str | None:
        """
        Рекурсивный поиск программы в указанном диске

        :param path: Стартовы путь для рекурсивного поиска
        :param program_full_name: Полное имя программы, включая расширение

        :return: Путь на найденную программу или None
        """
        item = None
        try:
            for item in Path(path).rglob(program_full_name):
                if self._check_working_path(str(item)):
                    return str(item)
        except PermissionError:
            logger.info(T.permission_error.format(path=path, item=str(item)))

        return None

    def _save_config(
        self, path: str, programme_full_name: str, config_file_path: str
    ) -> str:
        """
        Сохраняет путь к программе в конфигурационном файле

        :param path: Полный путь к программе.
        :param programme_full_name: Полное имя программы, включая расширение. Например - 7z.exe

        :return: Полный путь к программе
        """
        self.config_path[programme_full_name] = path

        if config_file_path:
            try:
                with open(config_file_path, "w", encoding="utf-8") as f:
                    json.dump(self.config_path, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.warning(T.error_saving_config.format(e=e))

        logger.debug(
            T.program_is_localed.format(path=path)
            if path.find("\\") != -1
            else T.program_in_system_path
        )
        return path
