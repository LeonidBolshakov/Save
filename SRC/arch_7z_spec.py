import subprocess
from pathlib import Path
import sys
import os
import logging

logger = logging.getLogger(__name__)  # Используем логгер по имени модуля


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
            seven_zip_path: str,
            password: str = "",
            work_dir: str | None = None,
    ):
        """
        :param arch_path: (str) Путь к архиву
        :param list_file: (str) Путь к файлу содержащему список файлов
        :param seven_zip_path: (str). Путь на программу 7z
        :param password: (str) Пароль. Опционально
        :param work_dir: (str): Рабочая директория. Опционально
        """
        self.password = password
        self.arch_path = arch_path
        self.list_file = list_file
        self.seven_zip_path = seven_zip_path  # Сохраняем путь на программу 7z
        self.work_dir = work_dir or os.getcwd()  # Текущая директория по умолчанию

        logger.debug("Инициализация Arch7zSpec с параметрами")
        self.check_all_params()

    def check_all_params(self):
        """Контроль параметров объекта"""
        self.check_arch()
        self.check_list_file()

    def check_arch(self):
        """Контроль архива"""

        # 1. Удаляем архив, если он существует
        if self.arch_path:
            arch_path = Path(self.arch_path)
        else:
            logger.error("Задано пустое имя архива")
            raise ValueError(f"Задано пустое имя архива")

        if arch_path.exists():
            if arch_path.is_file():
                logger.warning(
                    "Файл архива уже существует и будет удалён: %s", arch_path
                )
                arch_path.unlink()
            else:
                logger.error("Существует директория с именем архива: %s", arch_path)
                raise FileExistsError(
                    f"существует директория {arch_path}, имя которой, совпадает с именем архива. Архивация невозможна."
                )

        # 2. Проверяем расширение архива
        if arch_path.suffix != ".exe":
            logger.error("Недопустимое расширение файла архива: %s", arch_path.suffix)
            raise ValueError(
                f"Расширение имени файла архива {arch_path} должно быть exe. Архив cамораспаковывающийся"
            )

    def check_list_file(self):
        """Контроль имени списка архивируемых файлов"""
        # Проверяем существует ли список архивируемых файлов
        file_name = Path(self.list_file)
        if not file_name.exists():
            logger.error("Не найден файл списка для архивации: %s", file_name)
            raise FileNotFoundError(
                f"В параметрах задан несуществующий файл списка для архивации - {file_name}"
            )
        logger.debug("Файл списка существует: %s", file_name)

    def make_archive(self) -> bool:
        """
        Архивируем файлы, список которых передан.
        :return: True - архивация успешна, False - архивация провалена.
        """

        # Определяем кодировку для вывода
        encoding = "cp866" if sys.platform == "win32" else "utf-8"

        # Запускаем программу 7z
        cmd = [
            self.seven_zip_path,
            "a",  # Добавляем файлы в архив
            *(
                [f"-p{self.password}"] if self.password else []
            ),  # Если пароль не задан параметр не формируется
            "-mhe=on",  # Если задан пароль шифровать имена файлов
            "-sfx",  # Создавать самораспаковывающийся файл
            self.arch_path,
            f"@{self.list_file}",
            # Добавляем параметры для подавления вывода
            "-bso0",  # отключить вывод в stdout
            "-bsp0",  # отключить индикатор прогресса
        ]

        cmd_print = cmd.copy()
        cmd_print[2] = f"-p***************" if self.password else "Пароль не задан"
        # Если пароль не задан параметр не формируется
        logger.info("Запуск архивации: %s", cmd_print)

        try:
            process = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                encoding=encoding,
                errors="replace",  # Автозамена нечитаемых символов
                cwd=self.work_dir,  # Указываем рабочую директорию
            )
        except Exception as e:
            print(f"Ошибка архивации: {e}", file=sys.stderr)  # 🔸 Оригинальный вывод
            logger.exception("Ошибка при запуске процесса архивации")
            return False
        else:
            if process.returncode != 0:
                # Выводим ошибки с правильной кодировкой
                print("Ошибка архивации:", file=sys.stderr)
                print(process.stdout, file=sys.stderr)
                print(process.stderr, file=sys.stderr)
                logger.error("Ошибка архивации. Код возврата: %d", process.returncode)
                logger.error("stderr: %s", process.stderr)
                return False

            logger.info("Архивация завершена успешно")
            return True
