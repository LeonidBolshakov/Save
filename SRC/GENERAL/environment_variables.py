from dotenv import load_dotenv
import os
import keyring
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constant import Constant as C


class EnvironmentVariables:
    def __init__(self):
        # _setup_keyring_backend()
        self.app_name = C.APP_NAME
        self._read_env_vars()

    @staticmethod
    def _read_env_vars():
        if not load_dotenv(dotenv_path=C.DOTENV_PATH):
            raise EnvironmentError(f"Файл {C.DOTENV_PATH} не найден")

    def get_var(self, var_name: str, default: str = "") -> str | None:
        val = keyring.get_password(self.app_name, var_name)
        if val is not None:
            return val
        return os.getenv(var_name, default)

    def put_keyring_var(self, var_name: str, value: str) -> None:
        try:
            keyring.set_password(self.app_name, var_name, value)
            result = keyring.get_password(self.app_name, var_name)
            if result != value:
                error_msg = f"❌ {var_name} не сохранён в keyring! Записываемое значение не равно прочитанному."
                logger.critical(error_msg)
                raise RuntimeError(error_msg)
        except Exception as e:
            raise RuntimeError(f"Ошибка сохранения {var_name}: {str(e)}")

    def write_keyring_vars(self):
        for var in C.VARS_KEYRING:
            current = self.get_var(var)
            prompt = f"{var} = {current if current else '[пусто]'}, введите новое или Enter: "
            new_val = input(prompt).strip()
            if new_val:
                self.put_keyring_var(var, new_val)

    def validate_vars(self):
        missing = [var for var in C.VARS_REQUIRED if not self.get_var(var)]
        if missing:
            raise EnvironmentError(f"❌ Отсутствуют переменные: {', '.join(missing)}")


if __name__ == "__main__":
    env = EnvironmentVariables()
    env.write_keyring_vars()
