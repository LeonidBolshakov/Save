import logging

logger = logging.getLogger(__name__)

from SRC.YADISK.writefileyandexdisk import write_file_yandex_disk
from SRC.GENERAL.remotenameservice import RemoteNamesService
from SRC.GENERAL.constants import Constants as C


def write_file(local_path: str) -> str:
    """
    Диспетчер вызова систем загрузки на разные типы облачного хранилища.
    Пока реализовано только сохранение на Яндекс-Диск

    Args:
        local_path: Абсолютный путь к локальному файлу для загрузки

    Returns:
        str: Путь к загруженному файлу на Яндекс-Диске
    """
    remote_name_service = RemoteNamesService()
    return write_file_yandex_disk(
        local_path=local_path,
        remote_dir=C.ROOT_REMOTE_ARCHIVE_DIR,
        call_back_obj=remote_name_service,
    )
