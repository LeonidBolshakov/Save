# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# корень проекта
proj_root = os.path.abspath(".")

# список данных, которые нужно включить в EXE
datas = [
    (os.path.join(proj_root, "save_setup.ui"), "."),
]

a = Analysis(
    ['SRC/SETUP/save_setup.py'],
    pathex=[proj_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SaveSetup',
    icon=os.path.join(proj_root, "icon.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False
)
