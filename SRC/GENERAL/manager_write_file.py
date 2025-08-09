import logging

logger = logging.getLogger(__name__)

from SRC.YADISK.writefileyandexdisk import write_file_to_yandex_disk
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.remote_archive_naming import RemoteArchiveNaming
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


def write_file(local_path: str) -> str:
    """
    Диспетчер вызова систем загрузки на разные типы облачного хранилища.
    Пока реализовано только сохранение на Яндекс-Диск

    Args:
        local_path: Абсолютный путь к локальному файлу для загрузки

    Returns:
        str: Путь к загруженному в облако файлу
    """
    variables = EnvironmentVariables()

    root_remote_archive_dir = variables.get_var(
        C.ENV_ROOT_REMOTE_ARCHIVE_DIR, C.ROOT_REMOTE_ARCHIVE_DIR
    )

    programme_write_file = variables.get_var(
        C.ENV_FULL_ARCHIVER_NAME, C.FULL_NAME_SEVEN_Z
    )

    # noinspection PyUnreachableCode
    match programme_write_file:
        case C.FULL_NAME_SEVEN_Z:
            return write_file_to_yandex_disk(
                local_path=local_path,
                remote_dir=root_remote_archive_dir,
                call_back_obj=RemoteArchiveNaming(),
            )
        case _:
            raise ValueError(
                T.unregistered_program.format(env=C.ENV_PROGRAMME_WRITE_FILE)
            )
