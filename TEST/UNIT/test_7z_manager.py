import json
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch

from SRC.seven_z_manager import SevenZManager  # Замените на имя файла, где у вас класс


def test_real_workflow(tmp_path, monkeypatch):
    """Интеграционный тест реального сценария работы"""
    # Создание тестового 7z.exe
    test_7z = tmp_path / "7z.exe"
    test_7z.write_bytes(b"MZ...")  # Минимальный валидный PE-заголовок

    # Создание конфига
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"SEVEN_ZIP_PATH": str(test_7z)}))

    # Создаем корректный мок для subprocess.run
    class MockRun:
        def __call__(self, *args, **kwargs):
            class MockResult:
                returncode = 0

            return MockResult()

    # Мокаем subprocess.run
    monkeypatch.setattr("SRC.seven_z_manager.subprocess.run", MockRun())

    # Инициализация менеджера
    manager = SevenZManager(str(config_file))

    # Проверка работы
    assert manager.get_path() == str(test_7z)
    assert manager.config["SEVEN_ZIP_PATH"] == str(test_7z)


def test_main_function(capsys):
    with patch("SRC.seven_z_manager.SearchProgramme") as MockManager:
        instance = MockManager.return_value
        instance.get_path.return_value = "C:/found/7z.exe"

        from SRC.seven_z_manager import main

        main()

        captured = capsys.readouterr()
        assert "C:/found/7z.exe" in captured.out


def test_global_search_in_disk_permission_error(tmp_path):
    """Тест обработки PermissionError при поиске"""
    manager = SevenZManager()

    # Создаем тестовый файл, который будет вызывать ошибку при проверке
    test_file = tmp_path / "7z.exe"
    test_file.touch()  # Создаем пустой файл

    # Мокаем метод проверки файла
    def mock_check(path):
        if path == str(test_file):
            raise PermissionError("Access denied")
        return 1  # Для других файлов возвращаем "неработоспособен"

    with patch.object(manager, "_check_working_path", mock_check):
        # Вызываем поиск в директории
        result = manager._global_search_in_disk(str(tmp_path))

        # Проверяем что файл был пропущен
        assert result is None


@pytest.fixture
def temp_config_file():
    with tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".json") as f:
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


def test_check_working_path_valid(tmp_path):
    # Создание тестового "архиватора"
    fake_7z = tmp_path / "7z.exe"
    fake_7z.write_text("")  # Пустой файл

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = (
            0  # Имитируем результат успешного выполнения команды
        )

        result = SevenZManager._check_working_path(
            str(fake_7z)
        )  # Проверка правильного архиватора
        assert result == 0

        # Проверяем параметры вызова
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert str(fake_7z) in args[0]  # Проверяем путь к 7z.exe
        assert "a" in args[0]  # Команда добавления
        assert "-sfx" in args[0]  # Флаг самораспаковывающегося архива


def test_check_working_path_invalid_7z(tmp_path):
    """Тест на бинарник 7z, который возвращает ошибку"""
    fake_7z = tmp_path / "7z.exe"
    fake_7z.write_bytes(b"invalid binary")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        result = SevenZManager._check_working_path(str(fake_7z))
        assert result == 1
        mock_run.assert_called_once()


def test_check_working_path_invalid(tmp_path):
    fake_7z = tmp_path / "7z.exe"
    fake_7z.write_text("")

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Simulated error")
        result = SevenZManager._check_working_path(str(fake_7z))
        assert result == 1


def test_init_config_broken_json(temp_config_file):
    """Тест обработки битого JSON в конфиге"""
    temp_config_file.write_text("{invalid json}", encoding="utf-8")

    with patch("logging.Logger.warning") as mock_warning:
        manager = SevenZManager(str(temp_config_file))
        mock_warning.assert_called()
        assert manager.seven_zip_path is None


def test_check_working_path_missing():
    result = SevenZManager._check_working_path("nonexistent_path.exe")
    assert result == 2


def test_init_config_valid_path(temp_config_file):
    config = {"SEVEN_ZIP_PATH": "C:/fake/path/7z.exe"}
    temp_config_file.write_text(json.dumps(config), encoding="utf-8")

    with patch("pathlib.Path.exists", return_value=True), patch.object(
        SevenZManager, "_check_working_path", return_value=0
    ):
        manager = SevenZManager(str(temp_config_file))
        assert manager.seven_zip_path == "C:/fake/path/7z.exe"


def test_init_config_key_missing(temp_config_file):
    config = {"OTHER_KEY": "value"}
    temp_config_file.write_text(json.dumps(config), encoding="utf-8")

    with patch("pathlib.Path.exists", return_value=True), patch.object(
        SevenZManager, "_check_working_path", return_value=2
    ):
        manager = SevenZManager(str(temp_config_file))
        assert manager.seven_zip_path is None


def test_init_config_invalid_path_raises(temp_config_file):
    config = {"SEVEN_ZIP_PATH": "C:/broken/7z.exe"}
    temp_config_file.write_text(json.dumps(config), encoding="utf-8")

    with patch("pathlib.Path.exists", return_value=True), patch.object(
        SevenZManager, "_check_working_path", return_value=1
    ):
        with pytest.raises(ValueError):
            SevenZManager(str(temp_config_file))


def test_get_7z_path_cached():
    manager = SevenZManager()
    manager.seven_zip_path = "C:/cached/7z.exe"
    assert manager.get_path() == "C:/cached/7z.exe"


def test_get_7z_path_common_found():
    manager = SevenZManager()
    with patch.object(
        manager, "_check_common_paths", return_value="C:/common/7z.exe"
    ), patch.object(manager, "_save_config") as mock_save:
        path = manager.get_path()
        assert path == "C:/common/7z.exe"
        mock_save.assert_called_once()


def test_get_7z_path_global_found():
    manager = SevenZManager()
    with patch.object(manager, "_check_common_paths", return_value=None), patch.object(
        manager, "_global_search", return_value="D:/found/7z.exe"
    ), patch.object(manager, "_save_config") as mock_save:
        path = manager.get_path()
        assert path == "D:/found/7z.exe"
        mock_save.assert_called_once()


def test_check_common_paths_found():
    manager = SevenZManager()
    with patch.object(SevenZManager, "_check_working_path", return_value=0):
        assert manager._check_common_paths() == SevenZManager.DEFAULT_PATHS[0]


def test_check_common_paths_not_found():
    manager = SevenZManager()
    with patch.object(SevenZManager, "_check_working_path", return_value=2):
        assert manager._check_common_paths() is None


def test_save_config(temp_config_file):
    manager = SevenZManager(str(temp_config_file))
    manager._save_config("C:/saved/path/7z.exe")
    saved = json.loads(Path(temp_config_file).read_text(encoding="utf-8"))
    assert saved["SEVEN_ZIP_PATH"] == "C:/saved/path/7z.exe"
    assert manager.seven_zip_path == "C:/saved/path/7z.exe"


def test_get_available_drives_mocked():
    with patch("pathlib.Path.exists", return_value=True):
        drives = SevenZManager._get_available_drives()
        assert all(str(d).endswith(":\\") for d in drives)
