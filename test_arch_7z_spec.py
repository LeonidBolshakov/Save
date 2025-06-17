"""Тесты для класса Arch7zSpec"""

from pathlib import Path

import pytest

from arch_7z_spec import Arch7zSpec
import testdata


def test_good():
    """Тест без ошибочных данных"""
    assert testdata.good_execution_test() == True


def test_no_exe():
    """Тест. В расширении имени архива указано не exe"""
    with pytest.raises(ValueError, match="Расширение имени файла"):
        Arch7zSpec("arch.ex", "@file.txt", "plus").to_archive()


def test_exist_arch():
    """Тест. Файл с архивом существует до архивации"""
    arch_name = "arch.exe"
    list_file = f"@list.txt"
    data = testdata.TestData(arch_name, list_file)
    data.make_input_data()
    Path(arch_name).open("w")

    Arch7zSpec(arch_name, list_file).to_archive()

    assert data.compare_file_data() == True

    data.delete_input_data()


def test_exist_dir():
    """Тест. Существует директория с именем как у архива."""
    arch_name = "arch.exe"
    arch_path = Path(arch_name)

    if arch_path.exists():
        if arch_path.is_file():
            arch_path.unlink(missing_ok=True)
        else:
            arch_path.rmdir()

    arch_path.mkdir(exist_ok=True)
    with pytest.raises(FileExistsError, match="существует директория"):
        assert Arch7zSpec(arch_name, "@file.txt", "plus").to_archive() == True
    arch_path.rmdir()


def test_empty_name_arch():
    """Тест. Пустое имя архива"""
    with pytest.raises(ValueError, match="пустое"):
        Arch7zSpec("", "@file.txt", "plus").to_archive()


def test_no_sign():
    with pytest.raises(FileNotFoundError, match="начинаться на @"):
        Arch7zSpec("t.exe", "file.txt", "plus").to_archive()


def test_name_dir():
    name_arch = "t.exe"
    Path(name_arch).mkdir(exist_ok=True)

    with pytest.raises(FileExistsError):
        Arch7zSpec(name_arch, "@file.txt", "plus").to_archive()

    Path(name_arch).rmdir()
