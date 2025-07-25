from createremotepath import CreateRemotePath
import logging

logger = logging.getLogger(__name__)

from SRC.YADISK.writefileyandexdisk import write_file_yandex_disk


def write_file(local_path: str) -> str:
    """
    Диспетчер вызова систем загрузки на разные типы облачного хранилища.
    Пока реализовано только сохранение на Яндекс-Диск

    Args:
        local_path: Абсолютный путь к локальному файлу для загрузки

    Returns:
        str: Путь к загруженному файлу на Яндекс-Диске
    """
    create_remote_path = CreateRemotePath()
    return write_file_yandex_disk(
        local_path=local_path, call_back_obj=create_remote_path
    )
