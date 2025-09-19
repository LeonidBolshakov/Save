from os import environ
from typing import Protocol
from PyQt6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QTimeEdit,
    QPushButton,
)
from mypy.checkpattern import self_match_type_names

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C


class HasSchedulePanelUI(Protocol):
    label_task_location: QLabel
    label_program_path: QLabel
    lineEdit_task_name: QLineEdit
    textEdit_task_description: QPlainTextEdit
    spinBox_repeat: QSpinBox
    timeEdit_start_in: QTimeEdit
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
        self.repeat = ui.spinBox_repeat
        self.start_in = ui.timeEdit_start_in
        self.btn_freeze = ui.btn_freeze
        self.btn_delete = ui.btn_delete
        self.btn_apply = ui.btn_apply
        self.btn_undo = ui.btn_undo
        self.env = EnvironmentVariables()
        self.show_task_information()

    def show_task_information(self) -> None:
        self.find_task()

    def find_task(self) -> None:
        task_location = self.env.get_var(C.TASK_LOCATION)
        self.task_location.setText(task_location)
        task_name = self.env.get_var(C.TASK_NAME)
        self.task_name.setText(task_name)

        program_path = self.env.get_var(C.PROGRAM_PATH)
        self.program_path.setText(program_path)
        print(f"{task_location=}  {task_name=} {program_path=}")
