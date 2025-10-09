from typing import Protocol

from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTimeEdit,
    QPushButton,
    QWidget,
)
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
import SRC.SETUP.utils as utils


class HasSchedulePanelUI(Protocol):
    label_task_location: QLabel
    label_program_path: QLabel
    lineEdit_task_name: QLineEdit
    textEdit_task_description: QPlainTextEdit
    spinBox_task_repeat: QSpinBox
    timeEdit_task_start_in: QTimeEdit
    btn_apply: QPushButton
    btn_undo: QPushButton
    btn_freeze: QPushButton
    btn_delete: QPushButton


class SchedulePanel:
    def __init__(self, ui: HasSchedulePanelUI) -> None:
        self.task_location = ui.label_task_location
        self.program_path = ui.label_program_path
        self.task_name = ui.lineEdit_task_name
        self.task_description = ui.textEdit_task_description
        self.task_repeat = ui.spinBox_task_repeat
        self.task_start_in = ui.timeEdit_task_start_in
        self.btn_freeze = ui.btn_freeze
        self.btn_delete = ui.btn_delete
        self.btn_apply = ui.btn_apply
        self.btn_undo = ui.btn_undo
        self.env = EnvironmentVariables()
        self.show_task_information()

    def show_task_information(self) -> None:
        self.show_task()

    def show_task(self) -> None:
        self.set_widget_env_texts(self.task_location, C.TASK_LOCATION)
        self.set_widget_env_texts(self.task_name, C.TASK_NAME)
        self.set_widget_env_texts(self.program_path, C.PROGRAM_PATH)
        self.set_widget_env_texts(self.task_description, C.TASK_DESCRIPTION)
        self.set_widget_env_texts(self.task_repeat, C.TASK_REPEAT)
        self.set_widget_env_texts(self.task_start_in, C.TASK_START_IN)

    def set_widget_env_texts(
        self,
        widget: QWidget,
        var_name: str,
    ) -> None:
        value = self.env.get_var(var_name)
        if value is None:
            ret_code = utils.set_widget_texts(widget, value, empty=C.TEXT_EMPTY)
            if ret_code:
                print(f"Ошибка в переменной окружения {var_name}\n{ret_code}")
