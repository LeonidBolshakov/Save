import subprocess
from pathlib import Path
import sys


class Arch7zSpec:
    """
    Класс для работы со специфичным архивом 7z.
    Специфика архива:
    1. Формируется самораспаковывающейся архив.
    2. Архивируемые файлы передаются в виде списка файлов, записанного в файл.
    """

    def __init__(self, arch_name_: str, file_list: str, password: str = ""):
        """
        Инициализация объекта класса
        :param arch_name_: (str). Имя архива. Расширение имени файла должно быть '.exe'
        :param file_list: (str). Имя файла со списком архивируемых файлов. Имя должно начинаться на @
        :param password: (str). Опционально. Пароль архива.
        """
        self.password = password
        self.arch_name = arch_name_
        self.file_list = file_list

        self.check_all_params()

    def check_all_params(self):
        """Контроль параметров объекта"""
        self.check_arch_name()
        self.check_list_file()
        self.check_password()

    def check_arch_name(self):
        """Контроль архива"""

        # 1. Удаляем архив, если он существует
        if self.arch_name:
            arch_path = Path(self.arch_name)
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
        # 1. Проверяем является ли переданный файл списком файлов
        if self.file_list[0] != "@":
            raise FileNotFoundError(
                "Параметр file_list должен ссылаться на файл со списком файлов и начинаться на @"
            )
        # 2. Проверяем существует ли список архивируемых файлов
        file_name = self.file_list[1:]
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
                    "7z",
                    "a",  # Добавляем файлы в архив
                    *(
                        [f"-p{self.password}"] if self.password else []
                    ),  # Если пароль не задан параметр не формируется
                    "-mhe=on",  # Если задан пароль шифровать имена файлов
                    "-sfx",  # Создавать саморазархивирующийся файл
                    self.arch_name,
                    self.file_list,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors="replace",  # Автозамена нечитаемых символов
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


if __name__ == "__main__":
    """Проверка работы стандартного запуска программы"""
    from testdata import good_execution_test

    if good_execution_test():
        print("Программа завершилась успешно")
    else:
        print("Тест провален")
