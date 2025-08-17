
from datetime import date
from SRC.GENERAL.remote_archive_naming import RemoteArchiveNaming
def test_generate_directory_and_accept_numbers(monkeypatch):
    r = RemoteArchiveNaming()
    monkeypatch.setattr(r, "target_date", date(2025, 8, 17))
    dir_path = r.generate_path_remote_dir()
    assert "2025_08" in dir_path
    for name in ["archive_2025_08_17_1.7z", "archive_2025_08_17_2.7z"]:
        r.accept_remote_directory_element(name)
    file_path = r.generate_path_remote_file()
    assert file_path.endswith("_3.7z")
