import os
from pathlib import Path
from tqdm import tqdm


def recursive_search(base_path, pattern):
    """Генератор для рекурсивного поиска файлов с корректным прогресс-баром"""
    base_path = Path(base_path)
    directories = [base_path]
    all_items = []

    # Сначала собираем все элементы для точного подсчета
    with tqdm(desc="Сканирование", unit="объект", dynamic_ncols=True) as scan_bar:
        while directories:
            current_dir = directories.pop()
            try:
                with os.scandir(current_dir) as it:
                    entries = list(it)
            except (PermissionError, OSError):
                continue

            for entry in entries:
                try:
                    entry_path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        directories.append(entry_path)
                    all_items.append(entry_path)
                except OSError:
                    continue
                finally:
                    scan_bar.update(1)
                    scan_bar.set_postfix(dir=f"{current_dir}"[-30:].replace("\\", "/"))

    # Теперь обрабатываем файлы с нормальным прогресс-баром
    for item in tqdm(all_items, desc="Обработка", unit="файл", dynamic_ncols=True):
        if item.is_file() and item.match(pattern):
            try:
                # Ваша обработка файла здесь
                size = item.stat().st_size
            except (PermissionError, OSError):
                continue


# Пример использования
if __name__ == "__main__":
    base_path = "C:/"
    pattern = "7.exe"
    recursive_search(base_path, pattern)
