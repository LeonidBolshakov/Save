from dotenv import load_dotenv
from logging import getLogger
import os

from constant import Constant as C

logger = getLogger(__name__)


class Environment:
    def __init__(self):
        # Список обязательных переменных окружения с пояснениями
        self.required_vars = C.REQUIRED_VARS

        self._load_environment_vars()

    def _load_environment_vars(self):
        load_dotenv(
            dotenv_path=C.DOTENV_PATH
        )  # Загрузка локальных переменных окружения

        # Догрузка нужных системных переменных окружения
        my_global_keys = [
            key for key in os.environ.keys() if key.startswith(C.SECRET_KEY_START)
        ]

        for key in my_global_keys:
            os.environ[key] = os.environ[key]

        self._validate_required_vars()

    def _validate_required_vars(self) -> None:
        """Проверяет наличие и доступность обязательных переменных окружения.

        Переменные окружения загружаются из .env файла и системных переменных окружения.
        Если какие-то переменные отсутствуют, генерируется исключение EnvironmentError.

        Raises:
            EnvironmentError: Если отсутствуют одна или несколько обязательных переменных
        """
        missing = [var for var in self.required_vars if not os.getenv(var)]
        if missing:
            error_msg = (
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}"
            )
            logger.critical(error_msg)
            raise EnvironmentError(error_msg)
