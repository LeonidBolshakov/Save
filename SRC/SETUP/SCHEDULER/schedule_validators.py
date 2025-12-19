from pathlib import Path

from PyQt6.QtCore import QTime

# Недопустимые символы в именах файлов и директорий Windows
NULL_CHAR = "\x00"
INVALID_PATH_CHARACTERS = NULL_CHAR + r'\/:*?"<>|'

# Windows запрещает зарезервированные имена устройств DOS
# (CON, PRN, AUX, NUL, COM1–COM9, LPT1–LPT9)
RESERVED_DOS_DEVICE_NAMES = frozenset(
    {
        ".",
        "..",
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


def text_handler(text: str) -> bool:
    """
    Проверяет текст на отсутствие служебной подстроки NULL_CHAR.

    Возвращает:
        True, если текст не содержит NULL_CHAR, иначе False.
    """
    return NULL_CHAR not in text


def start_time_handler(text: str) -> bool:
    """
    Валидирует время запуска задачи.

    Ожидаемый формат: 'HH:MM'.

    Возвращает:
        True, если строка корректно парсится в QTime, иначе False.
    """
    time = QTime.fromString(text, "HH:mm")
    return time.isValid()


def task_name_handler(name: str) -> bool:
    """
    Проверяет корректность имени задачи планировщика.

    Условия:
        - непустая строка;
        - не начинается и не заканчивается пробелом;
        - не содержит недопустимых символов для имени файла/задачи;
        - длина не более 256 символов.
    """

    # 1. Не пустая строка
    if not isinstance(name, str) or name.strip() == "":
        return False

    # 2. Не начинается и не заканчивается пробелом
    if name[0] == " " or name[-1] == " ":
        return False

    # 3. Проверка недопустимых символов
    if any(ch in INVALID_PATH_CHARACTERS for ch in name):
        return False

    # 4. Проверка длины
    if len(name) > 256:
        return False

    return True


def task_directory_handler(text: str) -> bool:
    return directory_handler(text)


def file_path_handler(text: str) -> bool:
    base = text
    p = Path(text)
    if p.drive:
        base = text[len(p.drive) :]
    # анализуруем путь без драйвера.
    return directory_handler(base)


def directory_handler(text: str) -> bool:
    """
    Проверяет корректность (корневого) пути директории в стиле Windows.

    Условия:
        1. Строка не пуста.
        2. Путь является "корневым" (начинается с '\\' или '/').
        3. Каждая часть пути не содержит недопустимых символов/имён.
        4. Путь не заканчивается пробелом или точкой.
    """
    # 1. Проверяем пустое ли имя
    if is_empty_string(text):
        return True

    # 2. Проверяем абсолютность пути
    if not is_rooted_path(text):
        return False

    # 3, 4. Проверка недопустимых символов и имён для Windows
    if not check_parts_for_invalid_chars(text):
        return False

    # 5. Проверка недопустимости завершающих пробела и точки
    if not check_trailing_chars(text):
        return False

    return True


def is_empty_string(text: str) -> bool:
    return not isinstance(text, str) or not text


def is_rooted_path(text: str) -> bool:
    return text.startswith(("\\", "/"))


def check_parts_for_invalid_chars(text: str) -> bool:
    p = Path(text[1:])
    for part in p.parts:
        if len(part) > 250:
            return False
        if any(ch in INVALID_PATH_CHARACTERS for ch in part):
            return False
        if any(ord(ch) < 32 for ch in part):
            return False
        if Path(part).stem in RESERVED_DOS_DEVICE_NAMES:
            return False
    return True


def check_trailing_chars(text: str) -> bool:
    return not text.endswith((" ", "."))


def mask_days_handler(text: str) -> bool:
    """
    Проверяет, что строка является корректной двоичной маской дней недели.

    Ожидается строка из '0' и '1', интерпретируемая как целое число
    в диапазоне [0, 255].
    """
    try:
        value = int(text, 2)
    except ValueError, TypeError:
        return False
    return 0 <= value < 256
