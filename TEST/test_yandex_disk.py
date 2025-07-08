import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from SRC.yandex_disk import YandexDisk
from yadisk.exceptions import PathExistsError, ForbiddenError, UnauthorizedError


# Мокаем YandexOAuth и возвращаем фейковый токен
@pytest.fixture(autouse=True)
def mock_yandex_oauth():
    with patch("yandex_disk.YandexOAuth") as mock_auth:
        instance = mock_auth.return_value
        instance.get_token.return_value = "fake-token"
        yield instance


# Мокаем yadisk.YaDisk
@pytest.fixture
def mock_disk():
    with patch("yandex_disk.yadisk.YaDisk") as mock_yadisk:
        disk = mock_yadisk.return_value
        disk.get_meta.return_value = None
        disk.listdir.return_value = []
        yield disk


# Экземпляр YandexDisk с параметрами
@pytest.fixture
def ydisk(mock_disk):
    return YandexDisk(
        target_date=date(2023, 12, 31),
        archive_prefix="backup",
        archive_ext=".zip",
        archive_path="disk:/Backups",
    )


def test_initialization_calls(mock_disk, ydisk):
    """Проверка вызовов get_meta и mkdir при инициализации"""
    mock_disk.get_meta.assert_called_with("disk:/Backups")
    mock_disk.mkdir.assert_not_called()  # get_meta не вызывает исключение


def test_create_archive_name_first(ydisk, mock_disk):
    """Создание имени, если архивов нет"""
    mock_disk.listdir.return_value = []
    name = ydisk.create_archive_name()
    assert name == "backup_2023_12_31_1.zip"


def test_create_archive_name_existing_files(ydisk, mock_disk):
    """Создание имени, если архивы уже есть"""
    mock_file1 = MagicMock(name="backup_2023_12_31_1.zip")
    mock_file2 = MagicMock(name="backup_2023_12_31_3.zip")
    mock_file3 = MagicMock(name="otherfile.txt")

    mock_file1.name = "backup_2023_12_31_1.zip"
    mock_file2.name = "backup_2023_12_31_3.zip"
    mock_file3.name = "note.txt"

    mock_disk.listdir.return_value = [mock_file1, mock_file2, mock_file3]
    name = ydisk.create_archive_name()
    assert name == "backup_2023_12_31_4.zip"


def test_extract_file_num_valid(ydisk):
    assert ydisk._extract_file_num("backup_2023_12_31_9.zip") == 9
    assert ydisk._extract_file_num("backup_2023_12_31_15.zip") == 15


def test_extract_file_num_invalid(ydisk):
    assert ydisk._extract_file_num("backup_2023_12_31_.zip") is None
    assert ydisk._extract_file_num("randomname.zip") is None
    assert ydisk._extract_file_num("backup_2023_12_31_9.txt") is None


def test_get_file_nums_success(ydisk, mock_disk):
    file1 = MagicMock(name="backup_2023_12_31_1.zip")
    file2 = MagicMock(name="backup_2023_12_31_2.zip")
    file3 = MagicMock(name="note.txt")

    file1.name = "backup_2023_12_31_1.zip"
    file2.name = "backup_2023_12_31_2.zip"
    file3.name = "note.txt"

    mock_disk.listdir.return_value = [file1, file2, file3]
    result = ydisk._get_file_nums()
    assert result == [1, 2]


def test_get_file_nums_exception(ydisk, mock_disk):
    mock_disk.listdir.side_effect = Exception("Ошибка API")
    with pytest.raises(NotImplementedError) as excinfo:
        ydisk._get_file_nums()
    assert "Ошибка получения и обработке списка файлов" in str(excinfo.value)


def test_write_archive_success(ydisk, mock_disk):
    mock_disk.get_disk_info.return_value = {}
    mock_disk.upload.return_value = None
    result = ydisk.write_archive("local_file.zip")
    assert result is True
    mock_disk.upload.assert_called_once()


def test_write_archive_unauthorized(ydisk, mock_disk):
    mock_disk.get_disk_info.side_effect = UnauthorizedError("Недействительный токен")
    with pytest.raises(PermissionError, match="Недействительный токен Яндекс.Диск!"):
        ydisk.write_archive("local_file.zip")


def test_write_archive_path_exists(ydisk, mock_disk):
    mock_disk.get_disk_info.return_value = {}
    mock_disk.upload.side_effect = PathExistsError("File exists")
    result = ydisk.write_archive("local_file.zip")
    assert result is False


def test_write_archive_forbidden(ydisk, mock_disk):
    mock_disk.get_disk_info.return_value = {}
    mock_disk.upload.side_effect = ForbiddenError("No access")
    result = ydisk.write_archive("local_file.zip")
    assert result is False


def test_write_archive_generic_exception(ydisk, mock_disk):
    mock_disk.get_disk_info.return_value = {}
    mock_disk.upload.side_effect = RuntimeError("Network error")
    result = ydisk.write_archive("local_file.zip")
    assert result is False
