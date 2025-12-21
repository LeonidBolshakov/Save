"""Утилиты для работы с виджетами PyQt6 в панели планировщика.

Модуль содержит функции для:
- установки значения в виджеты разных типов (текст, время, числовые поля);
- работы с маской дней недели через набор QCheckBox в layout;
- формирования небольших HTML-сообщений для QTextEdit.

Все функции ориентированы на использование в SchedulePanel и связанных контроллерах.
"""

import html
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QTimeEdit,
    QWidget,
    QHBoxLayout,
    QCheckBox,
    QLayout,
    QLineEdit,
    QSpinBox,
)
from PyQt6.QtCore import Qt, QTime, QSignalBlocker
from PyQt6.QtGui import QTextCursor

NULL_CHAR = "\x00"
HTML_TEG = "[html]"
DAYS_IN_WEEK = 7
WEEKDAY_MAX_INDEX = DAYS_IN_WEEK - 1

WidgetHandler = Callable[[Any, str], str | None]


def process_weekdays_layout(layout: QLayout, text: str) -> str | None:
    """
    Устанавливает состояние чекбоксов внутри QHBoxLayout по битовой маске

    text:
      - '1111100'
      - или '0b1111100'
      - пустая строка → маска 0

    Ввод интерпретируется как двоичная строка фиксированной длины 7 бит:
      - первый символ строки — старший бит (bit6);
      - последний символ строки — младший бит (bit0).

    Соответствие виджетам:
      - первый виджет в layout соответствует старшему биту (bit6);
      - последний виджет — младшему (bit0).

    Это позволяет вводить маску привычно слева-направо (Пн→Вс), например "1111100".

    Важно: внутри layout должны находиться виджеты с методом setChecked (обычно QCheckBox).

    Returns:
        None при успехе или строку с описанием ошибки.
    """
    text = (text or "").strip()

    if not text:
        mask = 0
    else:
        try:
            # '0b1111100' или '1111100'
            mask = int(text, 2)
        except ValueError:
            return f"Некорректная битовая маска дней: {text!r}"

    for bit_index in range(layout.count()):
        item = layout.itemAt(bit_index)
        if item is None:
            continue

        w = item.widget()
        if w is None:
            continue

        if hasattr(w, "setChecked"):
            checked = bool(mask & 1 << (WEEKDAY_MAX_INDEX - bit_index))
            w.setChecked(checked)

    return None


def set_widget_value(
    widget: QWidget | QLayout, text: str, *, empty: str = ""
) -> str | None:
    """
    Универсальная установка значения для разных типов виджетов.

    Поддерживаются:
      - QLabel (текст метки);
      - QTextEdit (plain/html в зависимости от префикса [html]);
      - QPlainTextEdit;
      - QSpinBox (целые числа);
      - QTimeEdit (время формата HH:MM);
      - QLayout с чекбоксами дней недели (битовая маска).

    Returns:
      None при успехе или строку с текстом ошибки при проблеме.
    """
    value = text or empty

    # 1. Специальный случай — layout с днями недели (битовая маска)
    if isinstance(widget, QLayout):
        return process_weekdays_layout(widget, value)

    # 2. Диспетчеризация по типу виджета
    for cls, handler in WIDGET_HANDLERS:
        if isinstance(widget, cls):
            return handler(widget, value)

    # 3. Тип нами не поддерживается
    return f"Тип widget {type(widget)} программой не поддерживается"


def connect_checkboxes_in_layout(layout: QHBoxLayout, slot: Callable) -> None:
    """
    Подключает один слот ко всем чекбоксам внутри QHBoxLayout.

    Args:
        layout: Layout, содержащий QCheckBox-виджеты.
        slot:   Функция/метод, вызываемый при изменении состояния чекбокса.

    Используется, например, чтобы при любом изменении дня недели
    «подсветить» кнопки «создать»/«отменить изменения».
    """
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is not None:
            w = item.widget()
            if isinstance(w, QCheckBox):
                w.stateChanged.connect(slot)


def make_html(text: str, color: str) -> str:
    """
    Формирует небольшой HTML-фрагмент для вывода в QTextEdit.

    Особенности:
      - text экранируется (html.escape) и переводы строк '\n' заменяются на <br>;
      - параметр color задаёт цвет текста (например, 'green'/'red' или любой CSS-цвет);
      - насыщенность шрифта подбирается автоматически:
          * "green" — успешное сообщение (слегка жирный);
          * "red"   — ошибка (ещё более жирный);
          * прочее  — нейтральное информационное сообщение.

    Возвращаемая строка дополнительно помечается префиксом [html], чтобы
    её можно было корректно обработать в handle_text_edit().
    """
    # Экранируем спецсимволы и переводим \n в <br>
    safe_text = html.escape(text).replace("\n", "<br>")

    # Подбираем цвет и насыщенность шрифта
    if color == "green":  # успех
        css_color = "#2e7d32"
        font_weight = "500"
    elif color == "red":  # ошибка
        css_color = "#c62828"
        font_weight = "600"
    else:  # информационные сообщения
        css_color = color
        font_weight = "400"

    return (
        f"{HTML_TEG}"
        f'<div style="text-align:center;">'
        f'<span style="color:{css_color}; font-weight:{font_weight};">'
        f"{safe_text}"
        f"</span>"
        f"</div><br>"
    )


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def parse_time_hhmm(value: str) -> QTime | None:
    """
    Преобразует строку "HH:MM" в QTime.

    Returns:
        Объект QTime при корректной строке или None при ошибке формата.
    """
    q_time = QTime.fromString(value, "HH:mm")
    if q_time.isValid():
        return q_time
    return None


def handle_label(widget: QLabel, value: str) -> str | None:
    widget.setMouseTracking(True)
    widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    widget.setText(value)
    return None


def handle_text_edit(widget: QTextEdit, value: str) -> None:
    lower = value.lower()

    if lower.startswith(HTML_TEG):
        value = value[len(HTML_TEG) :].lstrip()
        widget.insertHtml(value)
        widget.moveCursor(QTextCursor.MoveOperation.End)
        return

    # Если не содержит тегов
    widget.setText(value)


def handle_plain_text(widget: QPlainTextEdit, value: str) -> str | None:
    with QSignalBlocker(widget.document()):
        widget.setPlainText(value)
    return None


def handle_spinbox(widget: QSpinBox, value: str) -> str | None:
    ivalue = parse_int(value)
    if ivalue is None:
        return f"Ожидалось целое число, а получено: {value!r}"
    widget.setValue(ivalue)
    return None


def handle_time_edit(widget: QTimeEdit, value: str) -> str | None:
    q_time = parse_time_hhmm(value)
    if q_time is None:
        return f"Время должно быть в формате HH:MM, а задано: {value!r}"
    widget.setTime(q_time)
    return None


WIDGET_HANDLERS: list[tuple[type, WidgetHandler]] = [
    (QLabel, handle_label),
    (QTextEdit, handle_text_edit),
    (QPlainTextEdit, handle_plain_text),
    (QSpinBox, handle_spinbox),
    (QTimeEdit, handle_time_edit),
    (QLineEdit, handle_text_edit),
]


def text_to_save_text(text: str) -> str:
    """Удаляет из текста NUL-символ (``\\x00``), который может ломать отображение/сохранение в Qt6."""
    return text.replace(NULL_CHAR, "")
