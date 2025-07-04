import subprocess
from pathlib import Path
import sys
import os


class Arch7zSpec:
    """
    Класс для работы со специфичным архивом 7z.
    Специфика архива:
    1. Формируется самораспаковывающейся архив.
    2. Архивируемые файлы передаются в виде списка файлов, записанного в файл.
    """

    def __init__(
        self,
        arch_path: str,
        list_file: str,
        password: str = "",
        sevenzip_path: str = r"C:\PycharmProjects\Save\7z",
        work_dir: str | None = None,
    ):
        """

        :param arch_path: (str) Имя архива
        :param list_file: (str) Имя файла содержащего список файлов
        :param password: (str) Пароль. Опционально
        :param sevenzip_path: (str). Путь на программу 7z
        """
        self.password = password
        self.arch_path = arch_path
        self.list_file = list_file
        self.sevenzip_path = sevenzip_path  # Сохраняем путь на программу 7z
        self.work_dir = work_dir or os.getcwd()  # Текущая директория по умолчанию

        self.check_all_params()

    def check_all_params(self):
        """Контроль параметров объекта"""
        self.check_arch()
        self.check_list_file()
        self.check_password()

    def check_arch(self):
        """Контроль архива"""

        # 1. Удаляем архив, если он существует
        if self.arch_path:
            arch_path = Path(self.arch_path)
        else:
            raise ValueError(f"Задано пустое имя архива")
        if arch_path.exists():
            if arch_path.is_file():
                arch_path.unlink()
            else:
                raise FileExistsError(
                    f"существует директория {arch_path}, имя которой, совпадает с именем архива. Архивация невозможна."
                )

        # 2. Проверяем расширение архива
        if arch_path.suffix != ".exe":
            raise ValueError(
                f"Расширение имени файла архива {arch_path} должно быть exe. Архив саморазархивирующийся"
            )

    def check_list_file(self):
        """Контроль имени списка архивируемых файлов"""
        # Проверяем существует ли список архивируемых файлов
        file_name = self.list_file
        if not Path(file_name).exists():
            raise FileNotFoundError(
                f"Задан несуществующий файл списка для архивации - {file_name}"
            )

    def check_password(self):
        """Экранируем пробелы в пароле"""
        if " " in self.password:
            self.password = f'"{self.password}"'

    def to_archive(self) -> bool:
        """
        Архивируем файлы, список которых передан.
        :return: True - архивация успешна, False - архивация провалена.
        """

        # Определяем кодировку для вывода
        encoding = "cp866" if sys.platform == "win32" else "utf-8"

        # Запускаем программу 7z
        try:
            process = subprocess.run(
                [
                    self.sevenzip_path,
                    "a",  # Добавляем файлы в архив
                    *(
                        [f"-p{self.password}"] if self.password else []
                    ),  # Если пароль не задан параметр не формируется
                    "-mhe=on",  # Если задан пароль шифровать имена файлов
                    "-sfx",  # Создавать саморазархивирующийся файл
                    self.arch_path,
                    f"@{self.list_file}",
                    # Добавляем параметры для подавления вывода
                    "-bso0",  # отключить вывод в stdout
                    "-bsp0",  # отключить индикатор прогресса
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors="replace",  # Автозамена нечитаемых символов
                cwd=self.work_dir,  # Указываем рабочую директорию
            )
        except Exception as e:
            print(f"Ошибка архивации: {e}", file=sys.stderr)
            return False
        else:
            if process.returncode != 0:
                # Выводим ошибки с правильной кодировкой
                print("Ошибка архивации:", file=sys.stderr)
                print(process.stdout, file=sys.stderr)
                print(process.stderr, file=sys.stderr)
                return False
            return True
