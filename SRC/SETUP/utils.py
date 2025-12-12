"""
Служебные программы для других модулей.

Содержит:
- функции сохранения/загрузки множества путей в файлы с обработкой ошибок;
- утилиты для отображения сообщений об ошибках пользователю (QMessageBox);
- вспомогательные парсеры и обработчики виджетов PyQt6;
- универсальную функцию set_widget_value для установки значений в разные типы виджетов;
- генератор небольшого HTML-фрагмента для вывода цветного текста в QTextEdit.
"""

import html
from pathlib import Path
from typing import Sequence, Callable, Any
from enum import Enum, IntFlag, auto
from loguru import logger

from PyQt6.QtWidgets import (
    QMessageBox,
    QWidget,
    QLabel,
    QHBoxLayout,
    QPlainTextEdit,
    QTextEdit,
    QTimeEdit,
    QSpinBox,
    QCheckBox,
    QLayout,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QTime

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C

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
HTML_TEG = "[html]"
DAYS_IN_WEEK = 7
WEEKDAY_MAX_INDEX = DAYS_IN_WEEK - 1


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


def save_set_to_file(items: set[str], list_archive_file_paths: str | Path) -> None:
    """Сохраняет множество путей в файл.

    Порядок в файле детерминирован (предварительная сортировка).

    Args:
        items: Множество полных путей отмеченных элементов
        list_archive_file_paths: Путь к файлу со списом архивируемых файлов.
    """
    p = Path(list_archive_file_paths)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        handle_error_message(3, p, e)
        return
    except OSError as e:
        handle_error_message(4, p, e)
        return

    try:
        p.write_text("\n".join(sorted(items)), encoding="utf-8")
    except PermissionError as e:
        handle_error_message(3, p, e)
    except OSError as e:
        handle_error_message(4, p, e)


def load_from_file(
    list_archive_file_paths: str | Path,
) -> tuple[list[str], list[str]]:
    """
    Читает файл со списком архивируемых файлов и делит их на существующие и отсутствующие.

    Args:
        list_archive_file_paths: путь к файлу со списком архивируемых файлов.

    Returns:
        (existing, deleted): два списка строк.

    """
    try:
        p = Path(list_archive_file_paths)
        nodes = p.read_text(encoding="utf-8").splitlines()
        existing, deleted = filter_existing(nodes)
    except PermissionError as e:
        handle_error_message(
            2, list_archive_file_paths, e, flags=FlagMessageError.CONFIRM
        )
        return [], []
    except FileNotFoundError:
        handle_error_message(0, list_archive_file_paths, flags=FlagMessageError.CONFIRM)
        return [], []
    except (OSError, UnicodeDecodeError, ValueError) as e:
        handle_error_message(
            1, list_archive_file_paths, e, flags=FlagMessageError.CONFIRM
        )
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
    Делит пути на существующие и не существующие.

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
    logger.error(_format_error_msg(template, p, e, full=True))

    # 2) Краткое сообщение пользователю (без e)
    msg = _format_error_msg(template, p, e, full=False)

    return handle_error(msg, flags)


def handle_error(msg: str, flags: FlagMessageError) -> ResultErrorMessage:
    """Форматирует сообщение, показывает пользователю,
        возвращает решение пользователя или выбрасывает UserAbort.
    :param msg: Текст сообщения об ошибке.
    :param flags: Флаги определяющие действия пользователя при запросе.
    :return: При ошибке — текст ошибки. Без ошибок — None.

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
                logger.error("Пользователь выбрал первый вариант")
                return ResultErrorMessage.DELETION_CHECK
            else:
                logger.error("Пользователь выбрал второй вариант")
                return ResultErrorMessage.SKIP_DELETION_CHECK
        # режим с возможным исключением
        if ok:
            logger.error("Пользователь согласился и продолжил работу")
            return ResultErrorMessage.YES
        else:
            logger.error("Пользователь отказался и прекратил работу.")
            raise UserAbort

    elif flags & FlagMessageError.UNCONFIRM:
        QMessageBox.warning(None, "Предупреждение", msg)
        return ResultErrorMessage.NO

    else:
        raise ValueError(f"Ошибка в программе. Непредусмотренный набор флагов: {flags}")


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


def process_weekdays_layout(
    layout: QLayout,
    text: str,
    *,
    empty: str = "",
) -> str | None:
    """
    Устанавливает состояние чекбоксов внутри QHBoxLayout по битовой маске

    text:
      - '1111100'
      - или '0b1111100'
      - пустая строка или `empty` → маска 0

    0-й бит → первый виджет в layout
    1-й бит → второй и т.д.

    Важно: внутри layout должны находиться виджеты с методом setChecked (обычно QCheckBox).

    Returns:
        None при успехе или строку с описанием ошибки.
    """
    text = (text or empty or "").strip()

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


def handle_label(widget: QLabel, value: str) -> str | None:
    widget.setMouseTracking(True)
    widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    widget.setText(value)
    return None


def handle_text_edit(widget: QTextEdit, value: str) -> None:
    lower = value.lower()

    if lower.startswith(HTML_TEG):
        value = value[len(HTML_TEG) :].lstrip()
        widget.setHtml(value)
        return

    # Если не содержит тегов
    widget.setText(value)


def handle_plain_text(widget: QPlainTextEdit, value: str) -> str | None:
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


WidgetHandler = Callable[[Any, str], str | None]

WIDGET_HANDLERS: list[tuple[type, WidgetHandler]] = [
    (QLabel, handle_label),
    (QTextEdit, handle_text_edit),
    (QPlainTextEdit, handle_plain_text),
    (QSpinBox, handle_spinbox),
    (QTimeEdit, handle_time_edit),
    (QLineEdit, handle_text_edit),
]


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
        return process_weekdays_layout(widget, value, empty=empty)

    # 2. Диспетчеризация по типу виджета
    for cls, handler in WIDGET_HANDLERS:
        if isinstance(widget, cls):
            return handler(widget, value)

    # 3. Тип нами не поддерживается
    return f"Тип widget {type(widget)} программой не поддерживается"


def connect_checkboxes_in_layout(
    layout: QHBoxLayout, slot: Callable[[int], None]
) -> None:
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
        css_color = color  # можно "black" или другой цвет
        font_weight = "400"

    return (
        f"{HTML_TEG}"
        f'<div style="text-align:center;">'
        f'<span style="color:{css_color}; font-weight:{font_weight};">'
        f"{safe_text}"
        f"</span>"
        f"</div>"
    )


def setup_logging() -> None:
    # добываем параметры
    variables = EnvironmentVariables()
    log_file_path = variables.get_var(
        C.ENV_LOG_SETUP_FILE_PATH, C.LOG_SETUP_FILE_PATH_DEF
    )
    level = variables.get_var(C.ENV_LOG_SETUP_LEVEL, C.LOG_SETUP_LEVEL_DEF)

    # Удаляем прежние логгеры, в т.ч по умолчанию
    logger.remove()

    # файл с ротацией
    logs_dir = Path(log_file_path).parent
    logs_dir.mkdir(exist_ok=True)
    logger.add(
        log_file_path,
        level=level,
        rotation="5 MB",
        retention="5 days",
        compression="zip",
    )
