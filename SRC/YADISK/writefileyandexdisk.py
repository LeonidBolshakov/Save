import logging

from SRC.YADISK.yandex_disk import YandexDisk
from SRC.GENERAL.remote_archive_naming import RemoteArchiveNamingProtokol
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT

logger = logging.getLogger(__name__)


def write_file_to_yandex_disk(
    local_path: str, remote_dir: str, call_back_obj: RemoteArchiveNamingProtokol
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
    try:
        yandex_disk = YandexDisk(remote_dir=remote_dir, call_back_obj=call_back_obj)
        if not (_remote_path := yandex_disk.write_file_fast(local_path)):
            raise OSError(YT.error_API_Yandex_disk)

        return _remote_path
    except Exception as e:
        raise RuntimeError(YT.error_ya_disk.format(e=e)) from e
