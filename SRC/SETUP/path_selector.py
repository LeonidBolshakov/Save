from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QLineEdit,
    QToolButton,
    QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFontMetrics


class PathSelector(QWidget):
    """
    Базовый абстрактный виджет выбора пути.

    Состав:
      [⚠]
      [ [ путь (QLineEdit, read-only) ] [ ... (QToolButton) ] ]

    Логика выбора пути вынесена в абстрактный метод choose_path(),
    который обязан быть переопределён в наследниках.

    Сигналы:
      path_changed(str) – новый выбранный путь.
    """

    path_changed = pyqtSignal(str)

    def __init__(
        self,
        path_edit: QLineEdit,
        choose_btn: QToolButton,
    ) -> None:
        super().__init__(None)

        self.path_edit = path_edit
        self.choose_btn = choose_btn
        self._full_path: str = ""

        self.choose_btn.clicked.connect(self.on_choose_clicked)

    # ---------- публичный API ----------

    def set_path(self, path: str) -> None:
        """Установить путь извне (и эмитить сигнал, если он изменился)."""
        path = str(path)

        if path == self._full_path:
            return
        self._full_path = path
        self._update_displayed_path()
        self.path_edit.setToolTip(self._full_path)
        # noinspection PyUnresolvedReferences
        self.path_changed.emit(self._full_path)

    def get_path(self) -> str:
        return self._full_path

    # ---------- абстрактная логика выбора пути ----------

    # @abstractmethod
    def choose_path(self) -> str:
        """
        Должен вернуть выбранный путь (строка) или "".
        Реализация обязана быть в наследниках.
        """
        raise NotImplementedError

    def on_choose_clicked(self) -> None:
        new_path = self.choose_path()
        if new_path:
            self.set_path(new_path)

    # ---------- отображение пути с усечением имени посередине ----------

    def _update_displayed_path(self) -> None:
        if not self._full_path:
            self.path_edit.setText("")
            return

        fm = QFontMetrics(self.path_edit.font())

        # ширина области, доступной для текста (учитывает рамки/паддинги)
        available_width = self.path_edit.contentsRect().width()
        if available_width <= 0:
            # виджет ещё не разложен по лейауту
            self.path_edit.setText(self._full_path)
            return

        elided = fm.elidedText(
            self._full_path,
            Qt.TextElideMode.ElideMiddle,
            available_width,
        )
        self.path_edit.setText(elided)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_displayed_path()


class ProgramSelector(PathSelector):
    """
    Выбор исполняемой программы.
    """

    def __init__(
        self,
        path_edit: QLineEdit,
        choose_btn: QToolButton,
    ) -> None:
        super().__init__(
            path_edit,
            choose_btn,
        )
        self.choose_btn.setToolTip("Выбрать программу")

    def choose_path(self) -> str:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите программу",
            "",
            "Исполняемые файлы (*.exe *.com *.bat);;Все файлы (*)",
        )
        return file_name or ""


class WorkDirSelector(PathSelector):
    """
    Выбор рабочей папки.
    """

    def __init__(
        self,
        path_edit: QLineEdit,
        choose_btn: QToolButton,
    ) -> None:
        super().__init__(
            path_edit,
            choose_btn,
        )
        self.choose_btn.setToolTip("Выбрать рабочую папку")

    def choose_path(self) -> str:
        dir_name = QFileDialog.getExistingDirectory(
            self,
            "Выберите рабочую папку",
            "",
        )
        return dir_name or ""
