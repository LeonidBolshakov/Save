# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files


a = Analysis(
    ['SRC\\GENERAL\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
	('_internal\\env', '.'),
	('_internal\\list.txt', '.'),
] + collect_data_files('password_strength') + collect_data_files('yadisk'),
    hiddenimports=collect_submodules('password_strength') + collect_submodules('yadisk'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='save_to_cload',
)