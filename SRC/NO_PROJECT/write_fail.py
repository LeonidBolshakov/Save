import logging

logger = logging.getLogger(__name__)

import yadisk
from yadisk.exceptions import (
    PathExistsError,
)

from SRC.YADISK.yandextextmessage import YandexTextMessage as YT


def write_file(self, local_path: str) -> bool:
    """
    Загружает локальный файл на Яндекс-Диск

    :param local_path: Путь к локальному файлу
    :return: Статус операции (True/False)
    """

    # Формируем полный путь на Яндекс-Диске
    remote_path = f"{self.remote_dir}/{self._create_remote_name()}"
    try:
        # Загрузка файла
        self._upload_file(local_path, remote_path)

        return True
    # Обработка специфических ошибок API
    except yadisk.exceptions.UnauthorizedError:
        logger.critical("")
        raise PermissionError(YT.invalid_token)
    except yadisk.exceptions.PathExistsError:
        raise PermissionError
    except yadisk.exceptions.ForbiddenError:
        logger.critical("")
        raise PermissionError
    except Exception as err:
        raise Exception(YT.error_load_file.format(err=err)) from err
