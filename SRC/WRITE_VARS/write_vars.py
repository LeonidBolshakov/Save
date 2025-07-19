"""
Ручная запись переменных в keyring
"""

from SRC.GENERAL.environment_variables import EnvironmentVariables

variables = EnvironmentVariables()
variables.write_keyring_vars()
