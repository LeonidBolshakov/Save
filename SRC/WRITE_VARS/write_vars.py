"""
Ручная запись переменных в keyring
"""

from pathlib import Path
import os

from SRC.GENERAL.environment_variables import EnvironmentVariables

parent_dir = Path.cwd().parent.parent
os.chdir(parent_dir)

variables = EnvironmentVariables()
variables.write_keyring_vars()
