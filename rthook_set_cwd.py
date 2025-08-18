# rthook_set_cwd.py — рабочая директория = папка EXE
import os, sys
from pathlib import Path
if getattr(sys, 'frozen', False):
    os.chdir(Path(sys.executable).parent)
