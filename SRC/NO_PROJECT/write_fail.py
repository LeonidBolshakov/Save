import logging

logger = logging.getLogger(__name__)

import yadisk
from yadisk.exceptions import (
    PathExistsError,
)

from SRC.GENERAL.textmessage import TextMessage as T


def write_file(self, local_path: str) -> bool:
    """
    Загружает локальный файл на Яндекс-Диск

    :param local_path: Путь к локальному файлу
    :return: Статус операции (True/False)
    """
    logger.info(T.start_load_file.format(local_path=local_path))

    # Формируем полный путь на Яндекс-Диске
    remote_path = f"{self.remote_dir}/{self.create_remote_name()}"
    try:
        # Загрузка файла
        self._upload_file(local_path, remote_path)

        return True
    # Обработка специфических ошибок API
    except yadisk.exceptions.UnauthorizedError:
        logger.critical("")
        raise PermissionError(T.invalid_token)
    except yadisk.exceptions.PathExistsError:
        raise PathExistsError(T.file_exists.format(remote_path=remote_path))
    except yadisk.exceptions.ForbiddenError:
        logger.critical("")
        raise PermissionError(T.not_enough_rights.format(remote_path=remote_path))
    except Exception as err:
        raise Exception(T.error_load_file.format(err=err)) from err
