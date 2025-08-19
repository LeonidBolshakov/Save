"""
rthook_init.py
==============
Runtime-hook для PyInstaller. Выполняется ПЕРЕД запуском вашего приложения,
когда exe уже распакован (в режиме --onefile).

Назначение:
- Переключить рабочую директорию (cwd) на папку с exe, чтобы относительные пути работали стабильно.
- Найти встроенную в сборку папку настроек/данных (C.SETTINGS_DIRECTORY_DEF).
- ОДИН РАЗ скопировать её в постоянный каталог пользователя и записать путь
  в переменную окружения C.ENVIRON_SETTINGS_DIRECTORY. Далее приложение
  использует только пользовательскую копию.

Важно:
- При запуске из IDE/интерпретатора (не exe) этот hook не выполняется автоматически.
  Если нужно повторить поведение в dev, импортируйте и вызовите _ensure_internal_copied()
  в ручную из кода запуска (например, в main.py).
"""

from __future__ import annotations

import os
import sys
import shutil
from pathlib import Path

# Константы проекта
from SRC.GENERAL.constants import Constants as C


def _set_cwd_to_exe_dir() -> None:
    """
    Делает текущей рабочей директорией папку, где расположен exe.
    Нужно для корректной работы относительных путей в собранном приложении.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        try:
            os.chdir(exe_dir)
        except Exception:
            # Игнорируем сбой смены каталога: приложение сможет работать с исходным cwd
            pass


def _user_data_dir(app_name: str) -> Path:
    """
    Возвращает путь к постоянному каталогу приложения для текущей ОС.

    Windows:   %APPDATA%\\{app_name}
    macOS:     ~/Library/Application Support/{app_name}
    Linux/BSD: $XDG_DATA_HOME/{app_name} либо ~/.local/share/{app_name}
    """
    home = Path.home()
    if sys.platform.startswith("win"):
        root = Path(os.environ.get("APPDATA", home))
        return root / app_name
    elif sys.platform == "darwin":
        return home / "Library" / "Application Support" / app_name
    else:
        return (
            Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / app_name
        )


def _resource_path(rel: str) -> Path:
    """
    Возвращает абсолютный путь к ресурсу внутри сборки.

    В exe: использует временную папку распаковки PyInstaller (sys._MEIPASS).
    В dev: берёт путь от текущей рабочей директории (cwd).
    """
    base = Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return base / rel


def _ensure_internal_copied() -> Path | None:
    """
    Гарантирует наличие пользовательской копии данных/настроек.

    Берёт источник:
        src = _resource_path(C.SETTINGS_DIRECTORY_DEF)
    и назначение:
        dst = _user_data_dir(C.KEYRING_APP_NAME) / C.SETTINGS_DIRECTORY_DEF
      либо, если C.SETTINGS_DIRECTORY_DEF уже абсолютная или включает подкаталоги,
      итоговый путь строится корректно через /.

    Действия:
      - если пользовательская копия отсутствует — копирует рекурсивно один раз;
      - выставляет переменную окружения C.ENVIRON_SETTINGS_DIRECTORY на конечный путь;
      - при ошибке даёт приложению работать со встроенной копией.
        В этом случае настройки работают только на чтение. Изменения не сохраняются.

    Возвращает:
        Path конечного каталога с данными, либо None, если исходной папки нет.
    """
    src = _resource_path(C.SETTINGS_DIRECTORY_DEF)
    if not src.exists():
        return None

    dst_root = _user_data_dir(C.KEYRING_APP_NAME)

    # Если SETTINGS_DIRECTORY_DEF это просто имя каталога — поместим его внутрь dst_root.
    # Если это составной путь (например, "config/_internal") — тоже корректно приклеим.
    dst = (dst_root / C.SETTINGS_DIRECTORY_DEF).resolve()

    try:
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)  # создаём родителя
            shutil.copytree(src, dst)  # копируем один раз

        # Пробрасываем путь в окружение для приложения
        os.environ[C.ENVIRON_SETTINGS_DIRECTORY] = str(dst)
        return dst
    except Exception:
        # Не удалось создать директорию - вариант "Б": работаем со встроенной копией
        os.environ[C.ENVIRON_SETTINGS_DIRECTORY] = str(src)
        return src


def _main() -> None:
    """Точка входа hook: выставить cwd и обеспечить пользовательскую копию данных."""
    _set_cwd_to_exe_dir()
    _ensure_internal_copied()


# Вызов при импортировании hook-скрипта PyInstaller'ом
_main()
