"""Типы UI-элементов и описание полей для SchedulePanel.

Содержит:
- HasSchedulePanelUI: протокол ожидаемого набора виджетов;
- ControlType: классификация типов полей для валидации;
- DescrTaskFields: описание одного поля (виджет, env-ключ, тип и тексты ошибок).
"""

from enum import Enum, auto
from typing import Protocol, Callable
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QTimeEdit,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QGroupBox,
    QLayout,
    QLineEdit,
    QToolButton,
)

HandlerType = Callable[[str], bool]


# fmt: off
class HasSchedulePanelUI(Protocol):
    """
    Протокол минимального набора атрибутов UI, необходимых SchedulePanel.

    Используется для статической проверки типов: любой объект, реализующий
    эти атрибуты, может быть передан в SchedulePanel.
    """
    label_task_location             : QLabel
    label_task_name                 : QLabel
    lineEdit_path_programm          : QLineEdit
    toolButton_path_programm        : QToolButton
    lineEdit_path_work_directory    : QLineEdit
    toolButton_work_directory       : QToolButton
    toolButton_work_directory_d     : QToolButton
    textEdit_task_description       : QPlainTextEdit
    timeEdit_task_start_in          : QTimeEdit
    btn_clean_all_day               : QPushButton
    btn_reject_changes              : QPushButton
    btn_select_all_day              : QPushButton
    btn_create_task                 : QPushButton
    btn_delete_task                 : QPushButton
    hbox_week_days                  : QHBoxLayout
    textEdit_Error                  : QTextEdit
    groupBoxLeft                    : QGroupBox

class ControlType(Enum):
    TEXT                            = auto()
    START_TIME                      = auto()
    FILE_PATH                       = auto()
    FOLDER_PATH                     = auto()
    TASK_NAME                       = auto()
    TASK_FOLDER                     = auto()
    MASK_DAYS                       = auto()


@dataclass
class DescrTaskFields:
    widget                          : QWidget | QLayout
    name_env                        : str
    control_type                    : ControlType
    error_text                      : str
    value_default                   : str | None = None
# fmt: on
