from PyQt6.QtWidgets import QLineEdit, QToolButton
from PyQt6.QtTest import QSignalSpy

from SRC.SETUP.SCHEDULER.scheduler_path_selector import PathSelector
import SRC.SETUP.SCHEDULER.scheduler_path_selector as m

SAMPLE_PATH = "C:/test/file.exe"
LONG_PATH = "C:/very/very/very/long/path/to/some/file.exe"


class DummySelector(PathSelector):
    def choose_path(self) -> str:
        return ""


def test_set_get_path_and_signal(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    s = DummySelector(edit, btn)

    spy = QSignalSpy(s.path_changed)

    s.set_path(SAMPLE_PATH)
    assert s.get_path() == SAMPLE_PATH
    assert edit.toolTip() == SAMPLE_PATH
    assert len(spy) == 1
    assert spy[0] == [SAMPLE_PATH]

    # Повторно записывем тот же путь -> нет нового сигнала
    s.set_path(SAMPLE_PATH)
    assert len(spy) == 1


def test_set_path_none_does_nothing(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    s = DummySelector(edit, btn)
    spy = QSignalSpy(s.path_changed)

    s.set_path(None)
    assert s.get_path() is None
    assert len(spy) == 0


def test_display_empty_path(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    s = DummySelector(edit, btn)
    spy = QSignalSpy(s.path_changed)

    s.set_path("")
    assert edit.text() == ""


def test_display_elide_does_not_grow(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    edit.resize(60, 20)  # маленькая ширина
    s = DummySelector(edit, btn)

    full = LONG_PATH
    s.set_path(full)

    assert edit.text()  # что-то отображается
    assert len(edit.text()) <= len(full)
    assert edit.toolTip() == full


def test_resize_triggers_recalc(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    s = DummySelector(edit, btn)
    s.set_path(LONG_PATH)

    edit.resize(40, 20)
    qtbot.wait(10)
    text_narrow = edit.text()
    tool_tip_narrow = edit.toolTip()

    edit.resize(400, 20)  # сильно шире
    qtbot.wait(10)
    text_wide = edit.text()
    tool_tip_wide = edit.toolTip()

    # На широкой строке обычно больше символов (или полный путь)
    assert len(text_wide) >= len(text_narrow)
    assert tool_tip_wide == tool_tip_narrow


def test_tooltip_not_affected_by_resize(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    s = DummySelector(edit, btn)
    s.set_path(LONG_PATH)
    initial = edit.toolTip()

    for w in (10, 50, 100, 500):
        edit.resize(w, 20)
        qtbot.wait(10)
        assert edit.toolTip() == initial


class ReturningSelector(PathSelector):
    def __init__(self, edit, btn, ret):
        super().__init__(edit, btn)
        self._ret = ret

    def choose_path(self) -> str:
        return self._ret


def test_on_choose_clicked_sets_path(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    s = ReturningSelector(edit, btn, "C:/a/b.exe")
    spy = QSignalSpy(s.path_changed)

    s.on_choose_clicked()
    assert s.get_path() == "C:/a/b.exe"
    assert len(spy) == 1


def test_on_choose_clicked_cancel_does_nothing(qtbot):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    initial_path = "C:/old.exe"
    s = ReturningSelector(edit, btn, None)
    s.set_path(initial_path)

    spy = QSignalSpy(s.path_changed)

    # дать доехать возможным queued/таймер-событиям от init
    qtbot.wait(0)

    before = len(spy)
    s.on_choose_clicked()
    qtbot.wait(0)

    assert s.get_path() == initial_path
    assert len(spy) == before


def test_program_selector_dialog_ok(qtbot, monkeypatch):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    monkeypatch.setattr(
        m.QFileDialog, "getOpenFileName", lambda *a, **k: ("C:/p.exe", "")
    )
    s = m.ProgramSelector(edit, btn)
    assert s.choose_path() == "C:/p.exe"


def test_program_selector_dialog_cancel(qtbot, monkeypatch):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    monkeypatch.setattr(m.QFileDialog, "getOpenFileName", lambda *a, **k: ("", ""))
    s = m.ProgramSelector(edit, btn)
    assert s.choose_path() is None


def test_workdir_selector_dialog_ok(qtbot, monkeypatch):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    monkeypatch.setattr(
        m.QFileDialog, "getExistingDirectory", lambda *a, **k: "C:/work"
    )
    s = m.WorkDirSelector(edit, btn)
    assert s.choose_path() == "C:/work"


def test_workdir_selector_dialog_cancel(qtbot, monkeypatch):
    edit = QLineEdit()
    btn = QToolButton()
    qtbot.addWidget(edit)
    qtbot.addWidget(btn)

    monkeypatch.setattr(m.QFileDialog, "getExistingDirectory", lambda *a, **k: "")
    s = m.WorkDirSelector(edit, btn)
    assert s.choose_path() is None
