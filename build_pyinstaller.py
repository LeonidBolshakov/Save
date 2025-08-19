from PyInstaller.__main__ import run

# Сборка в onefile. Папка _internal встраивается в bundle,
# а runtime-hook rthook_init.py при первом запуске копирует её
# в постоянную пользовательскую папку и выставляет переменную окружения INTERNAL_DIR.

run(
    [
        "--clean",
        "-y",
        "--onefile",
        "--noconsole",
        "--distpath",
        "dist/save_to_cload",
        "--add-data",
        "_internal;_internal",  # Windows формат; на *nix использовать ':'
        "--additional-hooks-dir",
        ".",
        "--runtime-hook",
        "rthook_init.py",
        "SRC/GENERAL/main.py",  # главный скрипт приложения
    ]
)
