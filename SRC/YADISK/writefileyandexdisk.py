import logging

logger = logging.getLogger(__name__)

from SRC.YADISK.yandex_disk import YandexDisk
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.createremotepath import RemotePathProtokol
from SRC.GENERAL.textmessage import TextMessage as T
from SRC.YADISK.yandexconst import YandexConstants as YC


def write_file_yandex_disk(local_path: str, call_back_obj: RemotePathProtokol) -> str:
    """Загружает файл на Яндекс-Диск используя API Яндекс.

    Args:
        local_path: Абсолютный путь к локальному файлу для загрузки
        call_back_obj: объект класса в котором будут использоваться 2 функции:

    Returns:
        str: Путь к загруженному файлу на Яндекс-Диске

    Raises:
        OSError: Если загрузка файла не удалась
        RuntimeError: При проблемах с API Яндекс-Диска
    """
    logger.info(T.init_load_to_disk)
    variables = EnvironmentVariables()
    try:
        port = int(variables.get_var(YC.ENV_YANDEX_PORT))
    except ValueError as e:
        logger.critical("")
        raise ValueError(T.invalid_port.format(e=e))

    try:
        yandex_disk = YandexDisk(port=port, call_back_obj=call_back_obj)
        if not (_remote_path := yandex_disk.write_file_fast(local_path)):
            logger.critical("")
            raise OSError(T.error_API_Yandex_disk)

        return _remote_path
    except Exception as e:
        raise
