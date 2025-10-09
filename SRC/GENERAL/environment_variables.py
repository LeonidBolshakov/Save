import dotenv
from pathlib import Path
import os
import logging

from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T

logger = logging.getLogger(__name__)

try:
    import keyring
except ImportError as err:
    logger.critical(T.not_keyring)
    raise ImportError() from err


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
        self.app_name = C.KEYRING_APP_NAME
        self.dotenv_path = (
            Path(os.environ.get(C.ENVIRON_SETTINGS_DIRECTORY, C.SETTINGS_DIRECTORY_DEF))
            / C.VARIABLES_DOTENV_NAME_DEF
        )
        self._custom_dot_env()

    def _custom_dot_env(self):
        """
        Загружает переменные из env файла.
        """

        # Загрузка переменных окружения
        if not dotenv.load_dotenv(dotenv_path=self.dotenv_path, encoding="utf-8"):
            logger.info(T.env_not_found.format(env=self.dotenv_path, dir=Path.cwd()))

    def get_var(self, var_name: str, default: str = "") -> str:
        """
        Получает значение переменной из keyring или окружения.

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
                        T.not_save_env.format(
                            var_name=var_name, value=value, result=result
                        )
                    )
            else:
                logger.error(T.not_save_env_empty.format(var_name=var_name))
        except Exception as e:
            logger.error(T.error_saving_env.format(var_name=var_name, e=e))

    def write_keyring_vars(self):
        """
        Позволяет пользователю ввести значения для всех переменных, указанных в `C.VARS_KEYRING`,
        и сохраняет их в keyring.
        """
        for var in C.VARS_KEYRING:
            current = self.get_var(var)
            prompt = T.prompt.format(var=var, current=current if current else T.empty)
            new_val = input(prompt)
            if new_val:
                self.put_keyring_var(var, new_val)

    def validate_vars(self):
        """
        Проверяет наличие всех обязательных переменных указанных в `C.VARS_REQUIRED`.
        Генерирует исключение, если какие-либо переменные отсутствуют.

        :raises EnvironmentError: При отсутствии одной или нескольких обязательных переменных.
        """
        missing = [var for var in C.VARS_REQUIRED if not self.get_var(var)]
        if not missing:
            return
        recorded_in_keyring = [var for var in C.VARS_KEYRING]
        missing_env = [var for var in missing if var not in recorded_in_keyring]
        missing_keyring = [var for var in missing if var in recorded_in_keyring]

        if missing_env:
            logger.error(
                T.missing_mandatory_variables_env.format(
                    dot_env=Path(self.dotenv_path).absolute(),
                    missing=", ".join(missing),
                )
            )
        if missing_keyring:
            logger.error(
                T.missing_mandatory_variables_keyring.format(
                    missing=", ".join(missing),
                )
            )

        raise RuntimeError(T.missing_mandatory_variables)


if __name__ == "__main__":
    # Если файл запускается как скрипт, то инициализируется класс и запускается ввод переменных
    parent_dir = Path.cwd().parent.parent
    os.chdir(parent_dir)

    env = EnvironmentVariables()
    env.write_keyring_vars()
