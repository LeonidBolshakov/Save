from freezegun import freeze_time
import pytest

from src.GENERAL.constants import Constants as C
from src.GENERAL import remote_archive_naming as naming_mod


class FakeVariables:
    def __init__(
        self,
        prefix: str = C.REMOTE_ARCHIVE_PREFIX_DEF,
        suffix: str = C.LOCAL_ARCHIVE_SUFFIX_DEF,
        root: str = C.ROOT_REMOTE_ARCHIVE_DIR,
    ):
        self.values = {
            C.ENV_REMOTE_ARCHIVING_PREFIX: prefix,
            C.ENV_LOCAL_ARCHIVE_SUFFIX: suffix,
            C.ENV_ROOT_REMOTE_ARCHIVE_DIR: root,
        }

    def get_var(self, name: str, default: str | None = None) -> str:
        return self.values.get(name, default or "")


@pytest.fixture(autouse=True)
def fake_environment(monkeypatch):
    monkeypatch.setattr(
        naming_mod,
        "EnvironmentVariables",
        lambda: FakeVariables(),
        raising=True,
    )


RemoteArchiveNaming = naming_mod.RemoteArchiveNaming


@freeze_time("2025-08-17")
def test_generate_directory_and_accept_numbers():
    r = RemoteArchiveNaming()

    dir_path = r.generate_path_remote_dir()
    assert "2025_08" in dir_path

    for name in ["archive_2025_08_17_1.7z", "archive_2025_08_17_2.7z"]:
        r.accept_remote_directory_element(name)

    file_path = r.generate_path_remote_file()
    assert file_path.endswith("_3.7z")


@freeze_time("2025-08-17")
def test_accept_ignores_none_and_non_matching_names():
    r = RemoteArchiveNaming()

    r.accept_remote_directory_element(None)
    r.accept_remote_directory_element("archive_2025_08_16_99.7z")
    r.accept_remote_directory_element("archive_2025_08_17_bad.7z")
    r.accept_remote_directory_element("other_2025_08_17_1.7z")

    assert r.file_nums == []
    assert r._extract_file_num("archive_2025_08_17_1.zip") is None


@freeze_time("2025-08-17")
def test_accept_is_case_insensitive_for_matching_archive_name():
    r = RemoteArchiveNaming()

    r.accept_remote_directory_element("ARCHIVE_2025_08_17_42.7Z")

    assert r.file_nums == [42]


@freeze_time("2025-08-17")
def test_extract_file_num_escapes_custom_prefix_and_suffix(monkeypatch):
    monkeypatch.setattr(
        naming_mod,
        "EnvironmentVariables",
        lambda: FakeVariables(prefix="arch.ve+", suffix=".tar.gz"),
        raising=True,
    )
    r = RemoteArchiveNaming()

    assert r._extract_file_num("arch.ve+_2025_08_17_12.tar.gz") == 12
    assert r._extract_file_num("archXve+_2025_08_17_12.tar.gz") is None
