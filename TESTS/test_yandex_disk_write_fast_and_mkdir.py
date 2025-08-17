from SRC.YADISK.yandex_disk import YandexDisk
import SRC.YADISK.yandex_disk as ymod


class DummyCB:
    def accept_remote_directory_element(self, name: str):
        pass

    def generate_path_remote_dir(self) -> str:
        return "/Архивы/2025_08"

    def generate_path_remote_file(self) -> str:
        return "/Архивы/2025_08/archive_2025_08_17_3.7z"


def _blank_init(self, remote_dir=None, call_back_obj=None):
    self.remote_dir = remote_dir
    self.call_back_obj = call_back_obj
    self.remote_path = None
    self.ya_disk = None


class FakeItem:
    def __init__(self, name):
        self.name = name


class ClientOK:
    def listdir(self, path):
        return [FakeItem("old.7z")]

    def exists(self, p):
        return True

    def mkdir(self, p):
        return None


class ClientEmpty:
    def listdir(self, path):
        return []

    def exists(self, p):
        return True

    def mkdir(self, p):
        return None


class UpOK:
    def __init__(self, ya, rp):
        self.ya, self.rp = ya, rp

    def write_file_direct(self, local_path):
        return None


class UpFail:
    def __init__(self, ya, rp):
        pass

    def write_file_direct(self, local_path):
        raise RuntimeError("upload fail")


def test_write_file_fast_success(monkeypatch, tmp_path):
    monkeypatch.setattr(YandexDisk, "__init__", _blank_init, raising=True)
    y = YandexDisk(remote_dir="/Архивы/2025_08", call_back_obj=DummyCB())

    # не позволяем вызывать реальный _get_ya_disk
    monkeypatch.setattr(
        YandexDisk, "_get_ya_disk", lambda self: ClientOK(), raising=True
    )
    y.ya_disk = ClientOK()

    monkeypatch.setattr(ymod, "UploaderToYaDisk", UpOK, raising=True)

    lp = tmp_path / "file.bin"
    lp.write_text("x")
    res = y.write_file_fast(str(lp))
    assert y.remote_path and y.remote_path.endswith(".7z")
    if res is not None:
        assert res.endswith(".7z")


def test_write_file_fast_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(YandexDisk, "__init__", _blank_init, raising=True)
    y = YandexDisk(remote_dir="/Архивы/2025_08", call_back_obj=DummyCB())

    monkeypatch.setattr(
        YandexDisk, "_get_ya_disk", lambda self: ClientEmpty(), raising=True
    )
    y.ya_disk = ClientEmpty()

    monkeypatch.setattr(ymod, "UploaderToYaDisk", UpFail, raising=True)

    lp = tmp_path / "file.bin"
    lp.write_text("x")
    out = y.write_file_fast(str(lp))
    assert out is None


def test_mkdir_custom_creates_all(monkeypatch):
    monkeypatch.setattr(YandexDisk, "__init__", _blank_init, raising=True)
    y = YandexDisk(remote_dir="/Архивы/2025_08", call_back_obj=DummyCB())

    created = []

    class Client:
        def exists(self, p):
            return p in ("/Архивы",)

        def mkdir(self, p):
            created.append(p)

    monkeypatch.setattr(YandexDisk, "_get_ya_disk", lambda self: Client(), raising=True)
    y.ya_disk = Client()

    path = y.mkdir_custom("/Архивы/2025_08/newdir")
    assert path.endswith("/Архивы/2025_08/newdir")
    assert created  # был хотя бы один mkdir
