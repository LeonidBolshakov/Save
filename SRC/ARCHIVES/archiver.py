from abc import ABC, abstractmethod


class Archiver(ABC):
    """Абстрактный класс для создания архивов"""

    def __init__(
        self,
        exe_path: str,
        work_dir: str | None = None,
    ) -> None:
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
        # noinspection PyUnresolvedReferences
        """Создаёт архив

        Args:
            archive_path: Путь к создаваемому архиву. Должен иметь правильное расширение
            list_file: Путь к файлу со списком файлов для архивации. Каждый файл должен быть на новой строке
            password: Пароль для архива. Если None, архив создается без шифрования
            compression_level: Уровень сжатия от 0 (без сжатия) до 9 (максимальное сжатие)

        Returns:
            int: Код возврата:
                - 0: успешное завершение
                - 1: нефатальные ошибки (например, некоторые файлы не были добавлены)
                - 2: фатальные ошибки (архив не создан)

        Raises:
            ValueError: При неверных параметрах
            FileNotFoundError: Если list_file не существует
            RuntimeError: При ошибках в процессе архивации

        Example:
            >>> archiver = ConcreteArchiver("c/program files/7-zip/7z.exe")
            >>> archiver.create_archive("out.exe", "files.txt", "password", 7)
            0
        """
        pass
