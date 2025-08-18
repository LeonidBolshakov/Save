# hook-password_strength.py — страховка для упаковки password_strength
from PyInstaller.utils.hooks import collect_all
datas, binaries, hiddenimports = collect_all('password_strength')
