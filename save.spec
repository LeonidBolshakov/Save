# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Собрать данные/бинарники/скрытые импорты зависимостей
ps_d, ps_b, ps_h = collect_all('password_strength')
yd_d, yd_b, yd_h = collect_all('yadisk')

datas = ps_d + yd_d + [('_internal', '_internal')]
binaries = ps_b + yd_b
hiddenimports = list(set(
    ps_h + yd_h +
    collect_submodules('password_strength') +
    collect_submodules('yadisk') +
    ['password_strength', 'yadisk']
))

a = Analysis(
    ['SRC\\GENERAL\\main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['rthook_set_cwd.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ONEFILE: включаем binaries/zipfiles/datas прямо в EXE, без COLLECT
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # смените на False, если нужен режим без консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
