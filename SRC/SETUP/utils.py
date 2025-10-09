"""
Служебные программы для других модулей
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence
from enum import Enum, IntFlag, auto

from PyQt6.QtWidgets import QMessageBox, QWidget, QLabel, QSpinBox, QTimeEdit
from PyQt6.QtCore import Qt, QTime

ERROR_TEXT = (
    "Файл '{p}' с пометками сохраняемых файлов/каталогов не обнаружен.\n"  # 0
    "Начинаем работу 'с чистого листа'?",
    "Нарушена структура файла '{p}' с пометками сохраняемых файлов/каталогов\n"  # 1
    "{e}\n"
    "Навсегда забываем ранее сделанные пометки?",
    "Нет доступа к файлу '{p}' с пометками сохраняемых файлов/каталогов\n"  # 2
    "{e}\n"
    "Навсегда забываем сделанные пометки?",
    "Не могу сохранить информацию об отмеченных файлах/каталогах. Нет доступа к файлу {p}\n"  # 3
    "{e}\n",
    "Не могу сохранить информацию об отмеченных файлах/каталогах. Ошибка вывода {p}\n"  # 4
    "{e}\n",
    "На диске удалены следующие файлы/каталоги, ранее отмеченные как сохраняемые:\n{p}\n\n"  # 5
    "Навсегда забываем, что про пометки удалённых файлов/каталогов? (Yes). Сохраняем пометки? (No)",
)
INIT_DELAY_MS = 100
COL0_WIDTH = 320
MAX_OUTPUT_DELETED = 10


class UserAbort(Exception):
    """Пользователь отказался продолжать выполнение операции."""


class FlagMessageError(IntFlag):  # Флаги для программы обработки ошибок
    CONFIRM = auto()  # Требует ответа пользователя
    NOT_RAISE = auto()  # При отказе пользователя работать, не выбрасывать исключение
    UNCONFIRM = auto()  # Не требует ответа пользователя


class ResultErrorMessage(Enum):  # Флаги return code программы обработки ошибок
    SKIP_DELETION_CHECK = (
        auto()
    )  # Пользователь: Не удалять отметки о ранее отмеченных, но впоследствии удалённых файлов/папок
    DELETION_CHECK = (
        auto()
    )  # Пользователь: Удалять отметки о ранее отмеченных, но впоследствии удалённых файлов/папок
    YES = auto()  # Пользователь ответил "Да"
    NO = auto()  # Пользователь ответил "Нет"


def save_set_json(items: set[str], path: str | Path = "marked elements.json") -> None:
    """Сохраняет множество путей в JSON-файл.

    Порядок в файле детерминирован (предварительная сортировка).

    Args:
        items: Множество полных путей отмеченных элементов
        path: Путь к JSON-файлу.
    """
    p = Path(path)

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        handle_error_message(3, p, e)
    except OSError as e:
        handle_error_message(4, p, e)

    try:
        # ensure_ascii=False — кириллица пишется «как есть» в UTF‑8.
        with p.open("w", encoding="utf-8") as f:
            json.dump(sorted(items), f, ensure_ascii=False, indent=2)
    except PermissionError as e:
        handle_error_message(3, p, e)
    except OSError as e:
        handle_error_message(4, p, e)


def load_set_json(
    path: str | Path = "marked elements.json",
) -> tuple[list[str], list[str]]:
    """
    Читает JSON со списком путей и делит их на существующие и отсутствующие.

    Args:
        path: путь к JSON-файлу.

    Returns:
        (existing, deleted): два списка строк.

    """
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as f:
            nodes = json.load(f)
        if not isinstance(nodes, (list, tuple)) or not all(
            isinstance(x, str) for x in nodes
        ):
            handle_error_message(1, p, flags=FlagMessageError.CONFIRM)
            return [], []
        existing, deleted = filter_existing(nodes)
    except PermissionError as e:
        handle_error_message(2, p, e, flags=FlagMessageError.CONFIRM)
        return [], []
    except FileNotFoundError:
        handle_error_message(0, p, flags=FlagMessageError.CONFIRM)
        return [], []
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
        handle_error_message(1, p, e, flags=FlagMessageError.CONFIRM)
        return [], []

    if deleted:
        deleted_out = deleted
        if MAX_OUTPUT_DELETED < len(deleted):
            deleted_out = deleted[: MAX_OUTPUT_DELETED - 1]
            deleted_out.append("...")

        ret_code = handle_error_message(
            5,
            "\n".join(deleted_out),
            flags=FlagMessageError.CONFIRM | FlagMessageError.NOT_RAISE,
        )
        if ret_code == ResultErrorMessage.SKIP_DELETION_CHECK:
            existing.extend(deleted)
            deleted.clear()
    return existing, deleted


def filter_existing(nodes: Sequence[str]) -> tuple[list[str], list[str]]:
    """
    Фильтрует список путей.

    Args:
        nodes: последовательность путей (str).

    Returns:
        (existing, deleted):
            existing — список существующих путей,
            deleted — список несуществующих путей.
    """
    existing: list[str] = []
    deleted: list[str] = []

    for node in nodes:  # проверка существования
        if Path(node).exists():
            existing.append(node)
        else:
            deleted.append(node)

    return existing, deleted


def _format_error_msg(
    template: str, p: Path | str | None, e: Exception | None, *, full: bool
) -> str:
    """Форматирует текст: с деталями при full=True, без них при full=False."""
    return template.format(p=p or "", e=str(e) if (e and full) else "")


def _ask_confirm(msg: str) -> bool:
    """Yes/No. True — продолжить."""
    btn = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    r = QMessageBox.question(
        None, "Подтверждение", msg, btn, QMessageBox.StandardButton.No
    )
    return r == QMessageBox.StandardButton.Yes


def handle_error_message(
    error_number: int,
    p: Path | str | None = None,
    e: Exception | None = None,
    *,
    flags: FlagMessageError = FlagMessageError.UNCONFIRM,
) -> ResultErrorMessage:
    """
    Формирует текст сообщения Пользователю, выводит лог,
    Передаёт управление для дальнейшей обработки ошибки.

    :param error_number: Номер ошибки.
    :param p: Уточняющая информация к сообщению об ошибке
    :param e: Exception, если ошибка вызвана прерыванием
    :param flags: Флаги определяющие возможности Пользователя при запросе.

    :return: Указание Пользователя программе по обработке ошибок.
    """
    template = ERROR_TEXT[error_number]

    # 1) Подробный лог (с e)
    print(_format_error_msg(template, p, e, full=True))

    # 2) Краткое сообщение пользователю (без e)
    msg = _format_error_msg(template, p, e, full=False)

    return handle_error(msg, flags)


def handle_error(msg: str, flags: FlagMessageError) -> ResultErrorMessage:
    """Форматирует сообщение, показывает пользователю,
        возвращает решение пользователя или выбрасывает UserAbort.
    :param msg: Текст сообщения об ошибке.
    :param flags: Флаги определяющие действия пользователя при запросе.
    :return: Указание Пользователя программе по обработке ошибок.

    Raises:
    UserAbort: Если confirm=True и пользователь выбрал No.
    ValueError: Если вызывающая программа задала конфликтующий набор флагов.
    """

    # взаимоисключающие флаги
    if (flags & FlagMessageError.CONFIRM) and (flags & FlagMessageError.UNCONFIRM):
        raise ValueError(f"Ошибка в программе. Несовместимые флаги: {flags}")

    if flags & FlagMessageError.CONFIRM:
        ok = _ask_confirm(msg)
        if flags & FlagMessageError.NOT_RAISE:
            if ok:
                print("Пользователь выбрал первый вариант")
                return ResultErrorMessage.DELETION_CHECK
            else:
                print("Пользователь выбрал второй вариант")
                return ResultErrorMessage.SKIP_DELETION_CHECK
        # режим с возможным исключением
        if ok:
            print("Пользователь согласился и продолжил работу")
            return ResultErrorMessage.YES
        else:
            print("Пользователь отказался и прекратил работу.")
            raise UserAbort

    elif flags & FlagMessageError.UNCONFIRM:
        QMessageBox.warning(None, "Предупреждение", msg)
        return ResultErrorMessage.NO

    else:
        raise ValueError(f"Ошибка в программе. Непредусмотренный набор флагов: {flags}")


def set_widget_texts(widget: QWidget, text: str, *, empty: str = "") -> str | None:
    """
    Устанавливает для виджета текст, tooltip и whatsThis.

    Args:
        widget (QWidget): Виджет, которому назначаются значения.
        text (str): Основной текст. Если пустой, берётся `empty`.
        empty (str, optional): Заглушка, если `text` пустой. По умолчанию "".
    """
    value = text or empty
    if hasattr(widget, "setText"):
        widget.setText(str(value))
    elif hasattr(widget, "setPlainText"):
        widget.setPlainText(str(value))
    elif isinstance(widget, QSpinBox):
        try:
            widget.setValue(int(value))
        except ValueError:
            return f"Задано не целое число {value}"
    elif isinstance(widget, QTimeEdit):
        # ожидается "HH:mm"
        q_time = QTime.fromString(value, "HH:mm")
        if not q_time.isValid():
            return f"Время задаётся в формате 'HH:MM', а задано {value}"
        widget.setTime(q_time)

    widget.setToolTip(value)
    widget.setWhatsThis(value)

    if isinstance(widget, QLabel):
        widget.setMouseTracking(True)
        widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    return None
