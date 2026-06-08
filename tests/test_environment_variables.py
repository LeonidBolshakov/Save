import pytest

from src.GENERAL import environment_variables as envmod
from src.GENERAL.constants import Constants as C


class MemoryKeyring:
    def __init__(self):
        self.store = {}

    def set_password(self, app, name, value):
        self.store[(app, name)] = value

    def get_password(self, app, name):
        return self.store.get((app, name))

    def delete_password(self, app, name):
        self.store.pop((app, name), None)


@pytest.fixture
def environment(monkeypatch, tmp_path):
    keyring = MemoryKeyring()
    monkeypatch.setattr(envmod, "keyring", keyring, raising=True)
    monkeypatch.setattr(envmod.utils, "get_env", lambda: tmp_path / "env", raising=True)
    monkeypatch.setattr(
        envmod.dotenv,
        "load_dotenv",
        lambda dotenv_path, encoding: False,
        raising=True,
    )

    for name in {"FOO_ENV", "SECRET", "EMPTY", *C.VARS_REQUIRED, *C.VARS_KEYRING}:
        monkeypatch.delenv(name, raising=False)

    return envmod.EnvironmentVariables(), keyring


def test_env_get_and_keyring_roundtrip(environment, monkeypatch):
    ev, keyring = environment

    assert ev.get_var("FOO_ENV", "default") == "default"
    assert ev.get_var("FOO_ENV") == ""

    ev.put_keyring_var("SECRET", "value123")
    assert keyring.get_password(ev.app_name, "SECRET") == "value123"
    assert ev.get_var("SECRET", "") == "value123"

    monkeypatch.setenv("FOO_ENV", "set")
    assert ev.get_var("FOO_ENV", "default") == "set"


def test_keyring_value_has_priority_over_environment(environment, monkeypatch):
    ev, keyring = environment
    monkeypatch.setenv("SECRET", "from-env")
    keyring.set_password(ev.app_name, "SECRET", "from-keyring")

    assert ev.get_var("SECRET", "default") == "from-keyring"


def test_put_keyring_var_ignores_empty_values(environment):
    ev, keyring = environment

    ev.put_keyring_var("EMPTY", "")

    assert keyring.get_password(ev.app_name, "EMPTY") is None


def test_write_keyring_vars_saves_only_entered_values(environment, monkeypatch):
    ev, keyring = environment
    monkeypatch.setattr(envmod.C, "VARS_KEYRING", ["ONE", "TWO"], raising=True)
    answers = iter(["first", ""])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))

    ev.write_keyring_vars()

    assert keyring.get_password(ev.app_name, "ONE") == "first"
    assert keyring.get_password(ev.app_name, "TWO") is None


def test_validate_vars_passes_when_required_values_exist(environment, monkeypatch):
    ev, keyring = environment

    for name in C.VARS_REQUIRED:
        if name in C.VARS_KEYRING:
            keyring.set_password(ev.app_name, name, "secret")
        else:
            monkeypatch.setenv(name, "value")

    ev.validate_vars()


def test_validate_vars_raises_when_required_values_are_missing(environment):
    ev, _ = environment

    with pytest.raises(RuntimeError):
        ev.validate_vars()
