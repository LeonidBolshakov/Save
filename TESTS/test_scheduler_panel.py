# tests/test_scheduler_panel_init.py
import types
from unittest.mock import MagicMock

import SRC.SETUP.SCHEDULER.scheduler_panel as scheduler_panel


def test_init_calls_base_stages(monkeypatch):
    """
    1) __init__ вызывает базовые этапы:
       _bind_ui, TaskFieldsController, init_button_styles, ErrorFormater,
       TaskSchedulerService, _init_ui_from_task_or_default, _init_path_selector, _btn_signal_connect.
    """
    calls = []  # Список вызовов функций

    # --- spies / fakes ---
    def spy_bind_ui(self, _ui):
        calls.append("_bind_ui")
        # чтобы __init__ не упал на чтении self.btn_create_task.text()
        self.btn_create_task = MagicMock()
        self.btn_create_task.text.return_value = "Create"

    def spy_init_ui_from_task_or_default(self):
        calls.append("_init_ui_from_task_or_default")

    def spy_init_path_selector(self):
        calls.append("_init_path_selector")

    def spy_btn_signal_connect(self):
        calls.append("_btn_signal_connect")

    # классы/функции-этапы, создаваемые в __init__
    TaskFieldsController_spy = MagicMock(
        side_effect=lambda _ui, cb: calls.append("TaskFieldsController") or MagicMock()
    )
    init_button_styles_spy = MagicMock(
        side_effect=lambda self: calls.append("init_button_styles")
    )
    ErrorFormater_spy = MagicMock(
        side_effect=lambda: calls.append("ErrorFormater") or MagicMock()
    )
    TaskSchedulerService_spy = MagicMock(
        side_effect=lambda cb: calls.append("TaskSchedulerService") or MagicMock()
    )

    monkeypatch.setattr(scheduler_panel.SchedulePanel, "_bind_ui", spy_bind_ui)
    monkeypatch.setattr(
        scheduler_panel.SchedulePanel,
        "_init_ui_from_task_or_default",
        spy_init_ui_from_task_or_default,
    )
    monkeypatch.setattr(
        scheduler_panel.SchedulePanel, "_init_path_selector", spy_init_path_selector
    )
    monkeypatch.setattr(
        scheduler_panel.SchedulePanel, "_btn_signal_connect", spy_btn_signal_connect
    )

    monkeypatch.setattr(
        scheduler_panel, "TaskFieldsController", TaskFieldsController_spy
    )
    monkeypatch.setattr(scheduler_panel, "init_button_styles", init_button_styles_spy)
    monkeypatch.setattr(scheduler_panel, "ErrorFormater", ErrorFormater_spy)
    monkeypatch.setattr(
        scheduler_panel, "TaskSchedulerService", TaskSchedulerService_spy
    )

    ui = MagicMock()

    # act
    scheduler_panel.SchedulePanel(ui)

    # assert (проверяем, что все этапы были вызваны)
    assert "_bind_ui" in calls
    assert "TaskFieldsController" in calls
    assert "init_button_styles" in calls
    assert "ErrorFormater" in calls
    assert "TaskSchedulerService" in calls
    assert "_init_ui_from_task_or_default" in calls
    assert "_init_path_selector" in calls
    assert "_btn_signal_connect" in calls


def test_init_ui_stops_when_create_task_path_returns_none(monkeypatch):
    """
    2) Если _create_task_path() -> None:
       - _try_load_task_and_update_ui не вызывается
       - UI переводится в ошибочное состояние через _set_error_ui_state
    """
    panel = scheduler_panel.SchedulePanel.__new__(scheduler_panel.SchedulePanel)

    # fields.apply_value_to_widget("task_folder"), затем ("task_name")
    panel.fields = MagicMock()
    panel.fields.apply_value_to_widget.side_effect = ["", "SomeName"]

    # spies
    panel._set_error_ui_state = MagicMock()
    panel._try_load_task_and_update_ui = MagicMock()

    # чтобы _init_ui_from_task_or_default не падал по атрибутам
    panel.btn_create_task = MagicMock()

    # на всякий случай фиксируем C.TEXT_NOT_TASK, если в окружении нет реального Constants
    if not hasattr(scheduler_panel, "C") or not hasattr(
        scheduler_panel.C, "TEXT_NOT_TASK"
    ):
        scheduler_panel.C = types.SimpleNamespace(TEXT_NOT_TASK="TEXT_NOT_TASK")

    # act
    panel._init_ui_from_task_or_default()

    # assert
    panel._set_error_ui_state.assert_called_once()  # вызывается внутри _create_task_path() при пустых folder/name
    panel._try_load_task_and_update_ui.assert_not_called()


def test_when_task_not_loaded_create_button_becomes_active(monkeypatch):
    """
    3) Если задача не загрузилась (_try_load_task_and_update_ui False) -> Create активируется:
       ожидание: set_button_create_active(btn_create_task, True) вызван.
    """
    panel = scheduler_panel.SchedulePanel.__new__(scheduler_panel.SchedulePanel)

    panel.btn_create_task = MagicMock()
    panel.set_button_create_active = MagicMock()

    # делаем так, чтобы путь создался, но загрузка задачи провалилась
    panel._create_task_path = MagicMock(return_value=r"\Folder\TaskName")
    panel._try_load_task_and_update_ui = MagicMock(return_value=False)

    # act
    panel._init_ui_from_task_or_default()

    # assert
    panel.set_button_create_active.assert_called_once_with(panel.btn_create_task, True)
