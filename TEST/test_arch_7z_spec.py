import os
import pytest
import subprocess
from pathlib import Path
from SRC.arch_7z_spec import Arch7zSpec


# Фикстура для пути к 7z
@pytest.fixture(scope="session")
def sevenzip_path():
    # Путь по умолчанию
    default_path = r"C:\Program Files\7-Zip\7z.exe"

    # Проверяем существование пути
    if Path(default_path).exists():
        return default_path

    # Проверяем переменную окружения
    env_path = os.environ.get("SEVENZIP_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    # Проверяем доступность в PATH
    try:
        subprocess.run(
            ["7z", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return "7z"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip(
            "7z not found. Install 7-Zip or set SEVENZIP_PATH environment variable"
        )


# Фикстура тестовых данных
@pytest.fixture
def test_data(tmp_path):
    # Создаем тестовые файлы
    files = []
    for i in range(3):
        file_path = tmp_path / f"test_file_{i}.txt"
        file_path.write_text(f"Test content {i}")
        files.append(file_path)
    return files


# Фикстура файла списка
@pytest.fixture
def list_file(tmp_path, test_data):
    """Создает файл списка с абсолютными путями"""
    list_path = tmp_path / "list_file.txt"

    with open(list_path, "w") as f:
        for file in test_data:
            # Записываем АБСОЛЮТНЫЕ пути
            f.write(f"{file}\n")

    return str(list_path)


# Фикстура пути архива
@pytest.fixture
def archive_path(tmp_path):
    return str(tmp_path / "test_archive.exe")


# Основной тест
def test_integration_archive(
    sevenzip_path, archive_path, list_file, test_data, tmp_path
):
    # 1. Создаем объект архивации
    arch = Arch7zSpec(
        arch_path=archive_path,
        list_file=list_file,
        password="secure_password",
        sevenzip_path=sevenzip_path,
        work_dir=str(tmp_path),  # Указываем рабочую директорию
    )

    # 2. Выполняем архивацию
    assert arch.to_archive() is True

    # 3. Проверяем архив
    archive_file = Path(archive_path)
    assert archive_file.exists()
    assert archive_file.stat().st_size > 1000

    # 4. Распаковываем
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    subprocess.run(
        [archive_path, f"-o{extract_dir}", "-y", f"-psecure_password"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # 5. Проверяем распакованные файлы
    for file in test_data:
        # Ищем файл по имени в распакованной директории
        found_files = list(extract_dir.rglob(file.name))
        assert (
            len(found_files) == 1
        ), f"Файл {file.name} не найден или найден несколько раз"

        extracted_file = found_files[0]
        assert extracted_file.read_text() == file.read_text()


# Тест с неправильным паролем
def test_wrong_password(sevenzip_path, archive_path, list_file, tmp_path):
    # Создаем архив
    arch = Arch7zSpec(
        arch_path=archive_path,
        list_file=list_file,
        password="correct_password",
        sevenzip_path=sevenzip_path,
    )
    assert arch.to_archive() is True

    # Пробуем распаковать с неправильным паролем
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(
            [sevenzip_path, "x", "-pwrong_password", f"-o{extract_dir}", archive_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,  # Вызовет исключение при ошибке
        )

    # Проверяем что файлы не распаковались
    assert not any(extract_dir.iterdir())


# Тест без пароля
def test_no_password(sevenzip_path, archive_path, list_file, test_data, tmp_path):
    # Создаем архив без пароля
    arch = Arch7zSpec(
        arch_path=archive_path,
        list_file=list_file,
        sevenzip_path=sevenzip_path,
    )
    assert arch.to_archive() is True

    # Распаковываем
    extract_dir = tmp_path / "extracted"
    extract_dir.mkdir()

    subprocess.run(
        [sevenzip_path, "x", f"-o{extract_dir}", archive_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Проверяем файлы
    for file in test_data:
        extracted_file = extract_dir / file.name
        assert extracted_file.exists()


# Тест обработки ошибок
def test_archive_failure(sevenzip_path, tmp_path):
    # Несуществующий файл списка
    with pytest.raises(FileNotFoundError):
        Arch7zSpec(
            arch_path=str(tmp_path / "archive.exe"),
            list_file="non_existent.txt",
            sevenzip_path=sevenzip_path,
        )


@pytest.fixture
def test_data_with_subdirs(tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()

    files = []
    for i in range(3):
        subdir = base_dir / f"dir_{i}"
        subdir.mkdir()

        file_path = subdir / f"file_{i}.txt"
        file_path.write_text(f"Content {i}")
        files.append(file_path)

    return files


@pytest.fixture
def test_data_special_chars(tmp_path):
    file_path = tmp_path / "файл с пробелами.txt"
    file_path.write_text("Тестовое содержимое")
    return [file_path]
