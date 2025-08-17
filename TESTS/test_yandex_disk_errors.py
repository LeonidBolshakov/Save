import pytest
from SRC.YADISK.yandex_disk import YandexDisk
from yadisk.exceptions import YaDiskError


class DummyCB:
    def accept_remote_directory_element(self, name: str):
        pass

    def generate_path_remote_dir(self) -> str:
        return "/Архивы/2025_08"

    def generate_path_remote_file(self) -> str:
        return "/Архивы/2025_08/archive_2025_08_17_3.7z"


def test_create_remote_dir_error(monkeypatch):
    # без сети, клиент с ошибкой на mkdir
    monkeypatch.setattr(
        YandexDisk, "get_token_for_API", lambda self: "TOKEN", raising=True
    )

    class BadClient:
        def exists(self, path):
            return False

        def mkdir(self, path):
            raise RuntimeError("fail")

    monkeypatch.setattr(
        YandexDisk, "init_ya_disk", lambda self, access_token: BadClient(), raising=True
    )

    with pytest.raises(YaDiskError):
        y = YandexDisk(remote_dir="/Архивы/2025_08", call_back_obj=DummyCB())
        # если конструктор не упал — добиваем явным вызовом
        y.create_remote_dir()
