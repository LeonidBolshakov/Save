from dotenv import load_dotenv
from pathlib import Path
import os
import keyring
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constant import Constant as C
from SRC.GENERAL.textmessage import TextMessage as T


class EnvironmentVariables:
    """
    Класс для работы с переменными окружения и хранилищем keyring.
    Поддерживает загрузку из .env, чтение/запись через keyring и валидацию обязательных переменных.
    """

    def __init__(self):
        """
        Инициализация класса.
        Загружает имя приложения из констант и читает переменные из .env файла.
        """
        self.app_name = C.APP_NAME
        self._read_env_vars()

    @staticmethod
    def _read_env_vars():
        """
        Загружает переменные из env файла.
        """
        # Блокировка выдачи спама
        for name in logging.root.manager.loggerDict:
            if name.startswith("dotenv"):
                logging.getLogger(name).setLevel(logging.INFO)

        # Загрузка переменных окружения
        if not load_dotenv(dotenv_path=C.DOTENV_PATH):
            logger.info(T.env_not_found.format(env=C.DOTENV_PATH, dir=Path.cwd()))

    def get_var(self, var_name: str, default: str = "") -> str | None:
        """
        Получает значение переменной из keyring или из окружения.

        :param var_name: Название переменной
        :param default: Значение по умолчанию, если переменная не найдена
        :return: Значение переменной или None
        """
        val = keyring.get_password(self.app_name, var_name)
        if val is not None:
            return val
        return os.getenv(var_name, default)

    def put_keyring_var(self, var_name: str, value: str) -> None:
        """
        Сохраняет переменную в keyring и проверяет корректность записи.

        :param var_name: Название переменной
        :param value: Значение для сохранения
        :raises RuntimeError: Если значение не удалось корректно сохранить
        """
        try:
            if value:
                keyring.set_password(self.app_name, var_name, value)
                result = keyring.get_password(self.app_name, var_name)
                if result != value:
                    raise RuntimeError(
                        f"❌ {var_name} не сохранён в keyring! Записываемое значение не равно прочитанному."
                    )
            else:
                raise RuntimeError(
                    f"❌ {var_name} не сохранён в keyring! Задано пустое значение."
                )
        except Exception as e:
            raise RuntimeError(f"Ошибка сохранения {var_name}: {str(e)}")

    def write_keyring_vars(self):
        """
        Позволяет пользователю ввести значения для всех переменных, указанных в `C.VARS_KEYRING`,
        и сохраняет их в keyring.
        """
        for var in C.VARS_KEYRING:
            current = self.get_var(var)
            prompt = f"{var} = {current if current else '[пусто]'}, введите новое или Enter: "
            new_val = input(prompt)
            if new_val:
                self.put_keyring_var(var, new_val)

    def validate_vars(self):
        """
        Проверяет наличие всех обязательных переменных из `C.VARS_REQUIRED`.
        Генерирует исключение, если какие-либо переменные отсутствуют.

        :raises EnvironmentError: При отсутствии одной или нескольких обязательных переменных.
        """
        missing = [var for var in C.VARS_REQUIRED if not self.get_var(var)]
        if missing:
            error_msg = f"❌ Отсутствуют переменные, задаваемые в файле {C.DOTENV_PATH} или в keyring:/n{', '.join(missing)}"
            logger.critical(error_msg)
            raise EnvironmentError(error_msg)


if __name__ == "__main__":
    # Если файл запускается как скрипт, то инициализируется класс и запускается ввод переменных
    parent_dir = Path.cwd().parent.parent
    os.chdir(parent_dir)

    env = EnvironmentVariables()
    env.write_keyring_vars()
