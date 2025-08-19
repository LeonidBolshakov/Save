# rthook_init.py — выполняется ПЕРЕД запуском приложения в сборке PyInstaller
# Задачи:
# 1) Сделать рабочую директорию равной папке с EXE
# 2) Скопировать встроенную в bundle папку _internal в постоянную директорию пользователя
# 3) Пробросить путь через переменную окружения INTERNAL_DIR

import os
import sys
import shutil
from pathlib import Path


def _set_cwd_to_exe_dir():
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        try:
            os.chdir(exe_dir)
        except Exception:
            pass


def _app_name():
    # используем имя исполняемого файла как имя приложения
    try:
        return Path(sys.executable).stem
    except Exception:
        return "App"


def _user_data_dir(app_name: str) -> Path:
    home = Path.home()
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", home))
        return root / app_name
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    else:
        # Linux/BSD
        return (
            Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / app_name
        )


def _resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return base / rel


def _ensure_internal_copied():
    src = _resource_path("_internal")
    if not src.exists():
        return None
    dst_root = _user_data_dir(r"Bolshakov\save")  # <- фиксированное имя
    dst = dst_root / "_internal"

    try:
        if not dst.exists():
            dst_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
        os.environ["INTERNAL_DIR"] = str(dst)
        return dst
    except Exception:
        os.environ["INTERNAL_DIR"] = str(src)
        return src


def _main():
    _set_cwd_to_exe_dir()
    _ensure_internal_copied()


_main()
