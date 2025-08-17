
import os
from SRC.GENERAL.environment_variables import EnvironmentVariables
def test_env_get_and_keyring_roundtrip():
    ev = EnvironmentVariables()
    os.environ.pop("FOO_ENV", None)
    assert ev.get_var("FOO_ENV", "default") == "default"
    ev.put_keyring_var("SECRET", "value123")
    assert ev.get_var("SECRET", "") == "value123"
    os.environ["FOO_ENV"] = "set"
    assert ev.get_var("FOO_ENV", "default") == "set"
