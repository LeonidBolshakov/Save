from __future__ import annotations
from pathlib import Path
import sys
import shutil


def get_user_dir() -> Path:
    """
    Папка, где будут лежать рабочие env и list.txt.
    Для Windows: %APPDATA%\\<C.SETTINGS_DIRECTORY>
    """
    appdata = os.getenv("APPDATA")
    if not appdata:
        # запасной вариант
        appdata = str(Path.home() / "AppData" / "Roaming")

    # используем то же имя каталога, что и в utils.get_list_archive_file_paths
    user_dir = Path(appdata) / C.SETTINGS_DIRECTORY
    user_dir.mkdir(parents=True, exist_ok=True)

    return user_dir


def get_internal_dir() -> Path:
    """
    Папка _Internal рядом с exe (в сборке)
    или рядом с корнем проекта (при запуске из исходников).

    Структура проекта:
        project_root/
            _Internal/
            SRC/
                GENERAL/
                    paths_win.py
    """
    if getattr(sys, "frozen", False):
        # запуск из exe
        base_dir = Path(sys.executable).parent
    else:
        # запуск из исходников:
        # __file__ = project_root/SRC/GENERAL/paths_win.py
        # parents[0] = .../SRC/GENERAL
        # parents[1] = .../SRC
        # parents[2] = .../project_root
        base_dir = Path(__file__).resolve().parents[2]

    return base_dir / "_Internal"


def prepare_files() -> Path:
    """
    Гарантирует наличие рабочей копии env в пользовательской папке.

    Возвращает:
        env_path — путь к рабочему env в %APPDATA%\\<C.SETTINGS_DIRECTORY>
    """
    internal_dir = get_internal_dir()
    user_dir = get_user_dir()

    env_src = internal_dir / "env"
    env_dst = user_dir / "env"

    # копируем только при первом запуске
    if not env_dst.exists() and env_src.exists():
        shutil.copy2(env_src, env_dst)

    return env_dst


from pathlib import Path
import os
from SRC.GENERAL.constants import Constants as C


def get_list_archive_file_paths() -> Path:
    """
    Путь к рабочему list.txt.
    Если файл ещё не существует — создаём пустой.
    """

    list_path = get_user_dir() / C.LIST_NAMS_OF_ARCHIVABLE_FILES

    # if not list_path.exists():  # ?????
    #     list_path.touch()

    return list_path


def get_env():
    return get_user_dir() / "env"


def resource_path(rel: str) -> Path:
    """
    Возвращает путь к UI в исходниках и собранном EXE.
    """
    # Запуск из PyInstaller onefile
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # noinspection PyProtectedMember
        base = Path(sys._MEIPASS)
        return base / rel

    # Запуск из проекта
    return Path(os.path.abspath(".")) / rel
