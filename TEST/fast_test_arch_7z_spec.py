import pytest
from pathlib import Path
import sys

from unittest.mock import patch, MagicMock

# Импорт тестируемого класса
from SRC.arch_7z_spec import Arch7zSpec


# Фикстуры
@pytest.fixture
def tmp_list_file(tmp_path):
    """Создает временный файл со списком для архивации."""
    file_path = tmp_path / "file_list.txt"
    file_path.write_text("test_file.txt")
    return str(file_path)


@pytest.fixture
def tmp_arch_path(tmp_path):
    """Возвращает временный путь для архива с расширением .exe."""
    return str(tmp_path / "test_archive.exe")


# Тесты
def test_init_success(tmp_arch_path, tmp_list_file):
    """Проверка успешной инициализации с корректными параметрами."""
    arch = Arch7zSpec(
        arch_path=tmp_arch_path, list_file=tmp_list_file, password="pass with space"
    )
    assert arch.arch_path == tmp_arch_path
    assert arch.list_file == tmp_list_file
    assert arch.password == '"pass with space"'


def test_check_arch_extension_fail(tmp_list_file):
    """Проверка ошибки при некорректном расширении архива."""
    with pytest.raises(ValueError, match="должно быть exe"):
        Arch7zSpec(arch_path="invalid.arc", list_file=tmp_list_file)


def test_check_arch_directory_conflict(tmp_path, tmp_list_file):
    """Проверка ошибки при конфликте с директорией."""
    dir_path = tmp_path / "conflict.exe"
    dir_path.mkdir()
    with pytest.raises(FileExistsError, match="директория"):
        Arch7zSpec(arch_path=str(dir_path), list_file=tmp_list_file)


def test_check_list_file_not_exists(tmp_arch_path):
    """Проверка ошибки при отсутствии файла списка."""
    with pytest.raises(FileNotFoundError):
        Arch7zSpec(arch_path=tmp_arch_path, list_file="missing.txt")


def test_password_escaping(tmp_arch_path: str, tmp_list_file: str):
    """Проверка экранирования пробелов в пароле."""
    arch = Arch7zSpec(tmp_arch_path, tmp_list_file, "pass with space")
    assert arch.password == '"pass with space"'


def test_password_without_spaces(tmp_arch_path: str, tmp_list_file: str):
    """Проверка пароля без пробелов."""
    arch = Arch7zSpec(tmp_arch_path, tmp_list_file, "password")
    assert arch.password == "password"


# noinspection SpellCheckingInspection
@patch("subprocess.run")
def test_to_archive_success(mock_run, tmp_arch_path, tmp_list_file):
    """Проверка успешной архивации."""
    # Настраиваем мок для успешного выполнения
    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    arch = Arch7zSpec(tmp_arch_path, tmp_list_file, "password")
    assert arch.make_archive() is True

    # Проверяем вызов команды
    expected_cmd = [
        r"C:\PycharmProjects\Save\7z",
        "a",
        "-ppassword",
        "-mhe=on",
        "-sfx",
        str(tmp_arch_path),
        # str(tmp_list_file),
        "@" + str(tmp_list_file),
        "-bso0",  # отключить вывод в stdout
        "-bsp0",  # отключить индикатор прогресса
    ]
    mock_run.assert_called_once()
    actual_cmd = mock_run.call_args[0][0]
    assert actual_cmd == expected_cmd


@patch("subprocess.run")
def test_to_archive_no_password(mock_run, tmp_arch_path, tmp_list_file):
    """Проверка архивации без пароля."""
    mock_run.return_value = MagicMock(returncode=0)

    arch = Arch7zSpec(tmp_arch_path, tmp_list_file)
    assert arch.make_archive() is True

    # Проверяем что параметр пароля отсутствует
    cmd = mock_run.call_args[0][0]
    assert "-p" not in " ".join(cmd)


@patch("subprocess.run")
def test_to_archive_failure(mock_run, tmp_arch_path, tmp_list_file, capsys):
    """Проверка обработки ошибки архивации."""
    # Настраиваем мок для возврата ошибки
    mock_run.return_value = MagicMock(
        returncode=1, stdout="Ошибка упаковки", stderr="Critical error"
    )

    arch = Arch7zSpec(tmp_arch_path, tmp_list_file)
    assert arch.make_archive() is False

    # Проверяем вывод ошибок
    captured = capsys.readouterr()
    assert "Ошибка архивации:" in captured.err
    assert "Ошибка упаковки" in captured.err
    assert "Critical error" in captured.err


@patch("subprocess.run", side_effect=Exception("Command failed"))
def test_to_archive_exception(mock_run, tmp_arch_path, tmp_list_file, capsys):
    """Проверка обработки исключения при архивации."""
    arch = Arch7zSpec(tmp_arch_path, tmp_list_file)
    assert arch.make_archive() is False
    captured = capsys.readouterr()
    assert "Ошибка архивации: Command failed" in captured.err


def test_arch_existing_file_removed(tmp_arch_path, tmp_list_file):
    """Проверка удаления существующего файла архива перед созданием."""
    # Создаем файл, который должен быть удален
    Path(tmp_arch_path).touch()
    arch = Arch7zSpec(arch_path=tmp_arch_path, list_file=tmp_list_file)
    assert not Path(tmp_arch_path).exists()  # Файл должен быть удален


def test_empty_arch_name(tmp_list_file):
    """Проверка обработки пустого имени архива."""
    with pytest.raises(ValueError, match="пустое имя архива"):
        Arch7zSpec(arch_path="", list_file=tmp_list_file)


def test_arch_removed_only_if_file(tmp_path, tmp_list_file):
    """Проверка того, что удаляется только файл, а директория вызывает ошибку."""
    # Создаем директорию с именем архива
    dir_path = tmp_path / "dir_archive.exe"
    dir_path.mkdir()

    # Проверяем что попытка использовать путь директории вызывает ошибку
    with pytest.raises(FileExistsError):
        Arch7zSpec(arch_path=str(dir_path), list_file=tmp_list_file)

    # Убедимся что директория не была удалена
    assert dir_path.exists() and dir_path.is_dir()


@patch("subprocess.run")
def test_windows_encoding(mock_run, tmp_arch_path, tmp_list_file, monkeypatch):
    """Проверка кодировки вывода на Windows."""
    monkeypatch.setattr(sys, "platform", "win32")
    mock_run.return_value = MagicMock(returncode=0)

    arch = Arch7zSpec(tmp_arch_path, tmp_list_file)
    arch.make_archive()

    # Проверяем что использовалась правильная кодировка
    mock_run.assert_called_once()
    kwargs = mock_run.call_args[1]
    assert kwargs["encoding"] == "cp866"


@patch("subprocess.run")
def test_non_windows_encoding(mock_run, tmp_arch_path, tmp_list_file, monkeypatch):
    """Проверка кодировки вывода на Linux/macOS."""
    monkeypatch.setattr(sys, "platform", "linux")
    mock_run.return_value = MagicMock(returncode=0)

    arch = Arch7zSpec(tmp_arch_path, tmp_list_file)
    arch.make_archive()

    # Проверяем что использовалась правильная кодировка
    mock_run.assert_called_once()
    kwargs = mock_run.call_args[1]
    assert kwargs["encoding"] == "utf-8"
