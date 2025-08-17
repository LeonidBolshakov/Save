
from SRC.GENERAL.backup_manager_7z import BackupManager7z
from SRC.ARCHIVES.archiver7z import Archiver7z
import SRC.GENERAL.backup_manager_abc as bmabc
def test_backup_manager_main_loop_success(monkeypatch, tmp_path):
    def fake_create(self, parameters_dict):
        p = (tmp_path / "local.7z")
        p.write_text("data")
        return str(p)
    monkeypatch.setattr(Archiver7z, "create_archive", fake_create, raising=True)
    def fake_write_file(local_path):
        return "/disk/ok/local.7z"
    monkeypatch.setattr(bmabc, "write_file", fake_write_file, raising=True)
    bm = BackupManager7z()
    remote = bm._main_program_loop()
    assert remote == "/disk/ok/local.7z"
