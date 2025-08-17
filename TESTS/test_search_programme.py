
from SRC.ARCHIVES.search_programme_abc import SearchProgramme

class DummySearch(SearchProgramme):
    def test_programme_execution(self, path: str) -> bool:
        return True

def test_search_in_config_and_standard_paths(tmp_path):
    conf = tmp_path / "config.json"
    std_dir = tmp_path / "std"
    std_dir.mkdir()
    (std_dir / "7z.exe").write_text("stub")
    s = DummySearch()
    found = s.get_path(str(conf), [str(std_dir)], "7z.exe")
    assert found == str(std_dir)

def test_search_absent_returns_programme_name(tmp_path):
    conf = tmp_path / "missing.json"
    s = DummySearch()
    found = s.get_path(str(conf), [str(tmp_path / 'nope')], "7z.exe")
    assert found == "7z.exe"
