from __future__ import annotations
from pathlib import Path
import sys
import os
import shutil

from src.GENERAL.constants import Constants as C


def get_user_dir() -> Path:
    """
    Папка, где будут лежать рабочие env и list.txt.mypy
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
    """

    base_dir = get_base_dir(2)  # project_root
    return base_dir / "_Internal"


def get_base_dir(folder_level: int = 2) -> Path:
    """
    Структура проекта:
        project_root/       folder_level=2
            _Internal/
            src/            folder_level = 1
                GENERAL/    folder_level = 0
                    paths_win.py
    """
    if getattr(sys, "frozen", False):
        # запуск из exe
        base_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        # запуск из исходников:
        # __file__ = project_root/src/GENERAL/paths_win.py
        # parents[0] = .../src/GENERAL
        # parents[1] = .../src
        # parents[2] = .../project_root
        base_dir = Path(__file__).resolve().parents[folder_level]

    return base_dir


def ensure_env_exists() -> Path:
    """
    Гарантирует наличие рабочей копии env в пользовательской папке.

    Возвращает:
        env_path — путь к рабочему env в %APPDATA%\\<C.SETTINGS_DIRECTORY>
    """
    internal_dir = get_internal_dir()
    user_dir = get_user_dir()

    env_src = internal_dir / "env"
    env_dst = user_dir / "env"

    # копируем только при необходимости
    if not env_dst.exists() and env_src.exists():
        shutil.copy2(env_src, env_dst)

    return env_dst


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
    base_dir = get_base_dir(1)  # src_root
    return base_dir / rel
