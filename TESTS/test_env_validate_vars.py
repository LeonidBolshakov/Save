import os
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C


def test_validate_vars_raises_when_missing(monkeypatch):
    # Ensure nothing in env or keyring
    for k in C.VARS_REQUIRED + C.VARS_KEYRING:
        os.environ.pop(k, None)

    ev = EnvironmentVariables()

    # Stub keyring to always return None
    ev.app_name = "APP"
    import SRC.GENERAL.environment_variables as envmod

    monkeypatch.setattr(
        envmod.keyring, "get_password", lambda app, name: None, raising=True
    )

    raised = False
    try:
        ev.validate_vars()
    except RuntimeError:
        raised = True
    assert raised
