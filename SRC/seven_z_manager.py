import subprocess  # Для запуска внешних процессов (7z.exe)
import string  # Для работы с наборами символов (диски)
import json  # Для работы с JSON-конфигурацией
from pathlib import Path  # Современный объектно-ориентированный путь
import tempfile  # Для создания временных файлов и директорий
import logging  # Для журнализации событий

# Создаем модульный логгер
logger = logging.getLogger(__name__)


class SevenZManager:
    """Класс для управления доступом к утилите архивации 7z.exe."""

    # Стандартные пути установки 7-Zip в Windows
    DEFAULT_PATHS = [
        "C:\\Program Files\\7-Zip\\7z.exe",
        "C:\\Program Files (x86)\\7-Zip\\7z.exe",
    ]

    # Шаблон имени искомого файла
    PATTERN_7_Z = "7z.exe"

    def __init__(self, file_config: str | None = None):
        """
        Инициализация менеджера 7z.

        :param file_config: Путь к JSON-файлу конфигурации (опционально)
        """
        self.seven_zip_path: str | None = None  # Кешированный путь к 7z.exe
        self.file_config: str | None = file_config  # Путь к файлу конфигурации
        self.config: dict = {}  # Словарь конфигурации
        self._init_config()  # Инициализация конфигурации

    def _init_config(self) -> None:
        """Загрузка и проверка конфигурации из файла."""
        if self.file_config and Path(self.file_config).exists():
            # Открытие и чтение файла конфигурации
            with open(self.file_config, "r", encoding="utf-8") as f:
                path = ""
                try:
                    # Парсинг JSON-конфигурации
                    self.config = json.load(f)
                    # Попытка получить путь к 7z из конфига
                    path = self.config["SEVEN_ZIP_PATH"]
                except KeyError:
                    # Обработка отсутствия нужного ключа
                    logger.warning(
                        f'В файле конфигураторе "{self.file_config}" нет ключа "SEVEN_ZIP_PATH"'
                    )
                except Exception as e:
                    # Общая обработка ошибок parsing
                    logger.warning(
                        f"Файл конфигуратора {self.file_config} содержит ошибки {e}"
                    )

            # Проверка работоспособности пути из конфига
            match self._check_working_path(path):
                case 0:  # Путь рабочий
                    self.seven_zip_path = path
                case 1:  # Программа неработоспособна
                    message = (
                        f"Программа {SevenZManager.PATTERN_7_Z} из конфига некорректна"
                    )
                    logger.critical(message)
                    raise ValueError(message)  # Прерываем инициализацию
                case 2:  # Путь не существует
                    message = f"В файле конфигураторе нет достоверной информации о расположении программы 7z.exe"
                    logger.warning(message)
                    raise ValueError(message)

    @staticmethod
    def _check_working_path(path: str) -> int:
        """
        Проверяет работоспособность 7z.exe по указанному пути.

        :param path: Путь к исполняемому файлу 7z
        :return:
            0 - программа работоспособна,
            1 - программа неработоспособна,
            2 - файл не существует
        """
        # Проверка существования файла
        if not (path and Path(path).exists()):
            return 2

        # Создание временной директории (автоматически удаляется после выхода)
        with tempfile.TemporaryDirectory() as tmpdir:
            test_archive = Path(tmpdir) / "test.exe"  # Временный архив
            test_file = Path(tmpdir) / "test.txt"  # Тестовый файл

            # Создание тестового файла
            test_file.write_text("Test", encoding="utf-8")

            # Попытка создания архива с помощью 7z
            # noinspection PyBroadException
            try:
                result = subprocess.run(
                    [
                        path,  # Путь к 7z.exe
                        "a",  # Команда добавления в архив
                        "-sfx",  # Создание самораспаковывающегося архива
                        str(test_archive),  # Имя архива
                        str(test_file),  # Архивируемый файл
                    ],
                    stdout=subprocess.DEVNULL,  # Игнорировать stdout
                    stderr=subprocess.DEVNULL,  # Игнорировать stderr
                    timeout=2,  # Таймаут выполнения
                )
                # Возвращаем 0 если процесс завершился успешно
                return 0 if result.returncode == 0 else 1
            # Обработка возможных ошибок выполнения
            except Exception:
                return 1

    def get_7z_path(self) -> str | None:
        """
        Основной метод получения пути к 7z.exe.

        Выполняет поиск в следующем порядке:
        1. Возвращает кешированный путь (если есть)
        2. Проверяет стандартные пути установки
        3. Выполняет глобальный поиск по всем дискам

        :return: Найденный путь или None
        """
        # Если путь уже известен - возвращаем его
        if self.seven_zip_path:
            return self.seven_zip_path

        # Поиск в стандартных местах установки
        if path := self._check_common_paths():
            self._save_config(path)  # Сохраняем в конфиг
            return path

        # Глобальный поиск по всем дискам
        if path := self._global_search():
            self._save_config(path)  # Сохраняем в конфиг
            return path

        return None  # 7z не найдена

    def _check_common_paths(self) -> str | None:
        """Проверка стандартных путей установки 7-Zip."""
        for path in SevenZManager.DEFAULT_PATHS:
            if self._check_working_path(path) == 0:
                return path
        return None

    def _global_search(self) -> str | None:
        """Инициирует поиск 7z.exe по всем доступным дискам."""
        logger.info(
            f"Начинаем поиск {SevenZManager.PATTERN_7_Z} по всем дискам... Это сможет занять некоторое время"
        )
        # Перебор всех доступных дисков
        for driver in self._get_available_drives():
            path = self._global_search_in_disk(str(driver))
            if path:
                return path
        return None

    def _global_search_in_disk(self, path: str) -> str | None:
        """
        Рекурсивный поиск 7z.exe в указанном диске/директории.

        :param path: Корневой путь для поиска
        :return: Найденный путь или None
        """
        # Рекурсивный обход файловой системы
        for item in Path(path).rglob(f"{SevenZManager.PATTERN_7_Z}"):
            try:
                # Проверка найденного файла
                if self._check_working_path(str(item)) == 0:
                    return str(item)
            except PermissionError:
                # Пропуск файлов без доступа
                pass
        return None

    def _save_config(self, path: Path | str) -> None:
        """
        Сохраняет путь к 7z в конфигурацию и файл (если указан).

        :param path: Путь к 7z.exe
        """
        str_path = str(path)
        self.seven_zip_path = str_path  # Кешируем путь
        self.config["SEVEN_ZIP_PATH"] = str_path  # Обновляем конфиг

        # Сохранение в файл если он указан
        if self.file_config:
            with open(self.file_config, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)

    @staticmethod
    def _get_available_drives() -> list[Path]:
        """Возвращает список доступных дисков в системе."""
        return [
            Path(f"{d}:\\") for d in string.ascii_uppercase if Path(f"{d}:\\").exists()
        ]


def main():
    try:
        seven_z_manager = SevenZManager("../TEST/config.json")
    except ValueError:
        print(f"Путь к {SevenZManager.PATTERN_7_Z} не найден")
    else:
        main_path = seven_z_manager.get_7z_path()
        print(
            main_path
            if main_path
            else f"Программа {SevenZManager.PATTERN_7_Z} не найдена. Установите программу"
        )


if __name__ == "__main__":
    main()
