import logging

logger = logging.getLogger(__name__)

from SRC.YADISK.yandex_disk import YandexDisk
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.remotenameservice import RemoteNamesServiceProtokol
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT
from SRC.YADISK.yandexconst import YandexConstants as YC


def write_file_yandex_disk(
    local_path: str, remote_dir: str, call_back_obj: RemoteNamesServiceProtokol
) -> str:
    """Загружает файл на Яндекс-Диск используя API Яндекс.

    Args:
        local_path: Абсолютный путь к локальному файлу для загрузки
        remote_dir: Директория на Яндекс-Диске, в которой находятся архивы.
        call_back_obj: объект класса в котором будут использоваться 2 функции:

    Returns:
        str: Путь к загруженному файлу на Яндекс-Диске

    Raises:
        OSError: Если загрузка файла не удалась
        RuntimeError: При проблемах с API Яндекс-Диска
    """
    logger.info(YT.init_load_to_disk)
    variables = EnvironmentVariables()
    try:
        port = int(variables.get_var(YC.ENV_YANDEX_PORT))
    except ValueError as e:
        raise ValueError(YT.invalid_port.format(e=e)) from e

    try:
        yandex_disk = YandexDisk(
            port=port, remote_dir=remote_dir, call_back_obj=call_back_obj
        )
        if not (_remote_path := yandex_disk.write_file_fast(local_path)):
            raise OSError(YT.error_API_Yandex_disk)

        return _remote_path
    except Exception as e:
        raise RuntimeError(YT.error_ya_disk.format(e=e)) from e
