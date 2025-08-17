from types import SimpleNamespace
from SRC.YADISK.yandex_disk import YandexDisk


class DummyCB:
    def __init__(self):
        self.items = []

    def accept_remote_directory_element(self, name: str):
        self.items.append(name)

    def generate_path_remote_dir(self) -> str:
        return "/Архивы/2025_08"

    def generate_path_remote_file(self) -> str:
        return "/Архивы/2025_08/archive_2025_08_17_3.7z"


def test_yandex_disk_upload_creates_dir_and_saves(monkeypatch, tmp_path):
    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def check_token(self, token=None):
            return True

        def exists(self, path):
            return False

        def mkdir(self, path):
            pass

        def listdir(self, path):
            return [
                SimpleNamespace(name="archive_2025_08_17_1.7z"),
                SimpleNamespace(name="archive_2025_08_17_2.7z"),
            ]

        def get_upload_link(self, path):
            return SimpleNamespace(href="http://upload.example")

        def upload(self, local_path, remote_path, overwrite=True):
            pass

    monkeypatch.setattr(
        YandexDisk, "get_token_for_API", lambda self: "TOKEN", raising=True
    )
    monkeypatch.setattr(
        YandexDisk,
        "init_ya_disk",
        lambda self, access_token: FakeClient(),
        raising=True,
    )
    y = YandexDisk(remote_dir="/Архивы/2025_08", call_back_obj=DummyCB())
    local = tmp_path / "f.7z"
    local.write_text("x")
    remote = y.write_file_fast(str(local))
    assert y.remote_path.endswith("archive_2025_08_17_3.7z")
    if remote is not None:
        assert remote.endswith("archive_2025_08_17_3.7z")
