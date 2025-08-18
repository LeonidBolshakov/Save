from PyInstaller.__main__ import run

run(["--clean", "-y", "--distpath", "dist/save_to_cload", "save.spec"])
