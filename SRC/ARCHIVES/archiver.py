from abc import ABC, abstractmethod


class Archiver(ABC):
    """Абстрактный класс для создания архивов"""

    def __init__(
        self,
        exe_path: str,
        work_dir: str | None = None,
    ):
        """
        Инициализирует экземпляр класса.

        Args:
            exe_path: Абсолютный путь к исполняемому файлу архиватора
            work_dir: Рабочая директория для выполнения команд архивации
                     (по умолчанию текущая директория)

        Raises:
            ValueError: Если не указан путь к архиву
            FileExistsError: Если по указанному пути архива уже существует файл/директория с именем архива
            FileNotFoundError: Если файл со списком архивируемых файлов не существует
        """

    @abstractmethod
    def create_archive(
        self,
        archive_path: str,
        list_file: str,
        password: str | None = None,
        compression_level: int = 5,
    ) -> int:
        """
        Создаёт архив

        :param archive_path: Путь к создаваемому архиву.
        :param list_file: Путь на файл со списком файлов для архивации.
        :param password: Пароль (опционально).
        :param compression_level: Уровень сжатия (0-9)

        :return: int: 0 если архивация успешна, 1 не фатальные ошибки, 2 - фатальные ошибки
        """
        pass
