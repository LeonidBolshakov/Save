"""Классы для работы (создание, удаление, сравнение) с тестовыми данными"""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Callable

from arch_7z_spec import Arch7zSpec


@dataclass
class DescrFile:
    """Класс описания создаваемого тестового файла"""

    file_name: str  # Имя файла
    file_data: list[str]  # Строки файла


def good_execution_test() -> bool:
    """
    Тест обычного выполнения архивирования
    :return: (bool). True - Архивирование успешно. False - архивирование провалено.
    """
    arch_name = "arch.exe"  # Имя архива
    list_file = "@list_file.txt"  # Имя файла со списком архивируемых файлов
    test_data = TestData(arch_name, list_file)  # Объект класса тестовых данных
    test_data.make_input_data()  # Создание данных для тестирования

    Arch7zSpec(arch_name, f"{list_file}").to_archive()  # Архивирование тестовых данных

    if (
        test_data.compare_file_data()
    ):  # Сравнение заархивированных -> разархивированных файлов с эталоном
        test_data.delete_files()
        return True
    else:
        return False


class TestData:
    """Класс формирует тестовые данные для архива, архивирует их, сравнивает разархивированные файлы и
    удаляет созданные файлы"""

    def __init__(self, arch_name: str, list_files: str):
        """
        Инициализация объекта
        :param arch_name: (str). Имя архива. Должно иметь расширение .exe. Файл формируется и удаляется внутри класса.
        :param list_files: (str). Имя файла для списка архивируемых файлов.
                                  Перед именем (первым символом имени) должен быть символ @.
                                  Файл формируется и удаляется внутри класса.
        """
        self.arch_name = arch_name
        self.list_files = list_files

        # Формирование описания тестируемых файлов
        self.files = []
        self.files.append(DescrFile("f1.txt", ["Строка1", "Строка2", "Строка3"]))
        self.files.append(DescrFile("f2.txt", ["Line 11", "Line 12"]))
        self.files.append(DescrFile("f3.txt", ["Файл 3"]))

    def delete_files(self) -> None:
        """Удаление всех созданных классом файлов"""
        self.delete_file(self.arch_name)  # Удаление архива
        self.delete_input_data()  # Удаление созданных архивируемых файлов

    @staticmethod
    def delete_file(file_name: str) -> None:
        """
        Удаление одного файла
        :param file_name: (str). Имя удаляемого файла
        :return: None
        """
        file_path = Path(file_name)

        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
            else:
                raise FileExistsError(
                    f"существует директория {file_path}, имя которой, совпадает с именем тестируемого файла. "
                    f"Тестирование невозможно."
                )

    @staticmethod
    def make_file(f: DescrFile) -> None:
        """
        Создание архивируемого файла
        :param f: (DescrFile). Описание создаваемого файла
        :return: None
        """
        try:
            with open(f.file_name, "w", encoding="utf-8") as file:
                file.write("\n".join(f.file_data))
        except Exception as e:
            raise FileExistsError(
                f"Доступ к файлу {f.file_name} закрыт - {e}. Тестирование невозможно."
            )

    def make_input_data(self) -> None:
        """Подготовка входных данных для тестирования"""
        self.delete_file(self.arch_name)

        self.make_file(  # Создание файла со списком файлов, подлежащих архивированию.
            DescrFile(self.list_files[1:], [files.file_name for files in self.files])
        )
        for file in self.files:  # Создание архивируемых файлов
            self.make_file(file)

    def delete_input_data(self) -> None:
        """Удаление входных файлов, предназначенных для архивации"""
        self.delete_file(self.list_files)  # Удаление файла со списком файлов
        for file in self.files:  # Удаление архивируемых файлов
            self.delete_file(file.file_name)

    def unzip(self) -> None:
        """Разархивация файлов из созданного архива"""
        self.delete_input_data()  # Удаление ранее заархивированных данных

        subprocess.run(  # Разархивирование данных
            [
                self.arch_name,
            ],
            stdout=subprocess.DEVNULL,
            errors="replace",
        )

    def compare_file_data(self) -> bool:
        """
        Сравнение разархивированных файлов с эталонами
        :return: True - сравнение удачно. False - сравнение провалено
        """
        self.unzip()
        for file in self.files:
            try:
                with open(file.file_name, encoding="utf-8") as f_unzipped:
                    # Читаем содержимое файла
                    file_content = f_unzipped.read()
                    if file_content != "\n".join(
                        file.file_data
                    ):  # Сравнение содержимого файла с эталоном
                        print(
                            f"Тест провален {"".join(f_unzipped.readlines())=} {"\n".join(file.file_data)=}"
                        )
                        return False
            except FileNotFoundError:
                print(f"Тест провален. Не могу открыть файл {file.file_name}")
                return False
        return True
