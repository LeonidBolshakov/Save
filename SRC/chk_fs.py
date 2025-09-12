"""
Файловый браузер на PyQt6 с checkboxes в дереве.

Возможности:
- Чекбокс у каждого элемента (только в колонке 0).
- Если отмечена папка, все её потомки:
  - подсвечиваются серым текстом (визуальный disabled-эффект);
  - блокируют изменение своего чекбокса.
- Отмеченные элементы подсвечиваются тёмно-синим текстом.
- Кнопки: выбрать видимые, очистить, вывести список отмеченных.
- Корень представления — вся файловая система (список дисков в Windows, "/" в Unix).

Зависимости: PyQt6.

Как запустить:
    python debug.py
"""

from __future__ import annotations
import sys
from typing import Any

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView, QPushButton
from PyQt6.QtCore import Qt, QIdentityProxyModel, QModelIndex, QDir
from PyQt6.QtGui import QFileSystemModel, QBrush


class CheckableFSModel(QIdentityProxyModel):
    """
    Прокси-модель, которая добавляет checkboxes и правила блокировки/подсветки
    поверх исходной QFileSystemModel.

    Хранит состояния checkboxes в словаре self._checks по абсолютному пути.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Карта: путь -> состояние чекбокса
        self._checks: dict[str, Qt.CheckState] = {}

    # ===== Вспомогательные методы =====

    def _path(self, index: QModelIndex) -> str:
        """
        Вернуть абсолютный путь элемента исходной модели для прокси-индекса.
        Пустая строка, если sourceModel не QFileSystemModel.
        """
        src = self.mapToSource(index)
        model = self.sourceModel()
        if isinstance(model, QFileSystemModel):
            return model.filePath(src)
        return ""

    def _is_dir(self, index: QModelIndex) -> bool:
        """Проверить, что индекс указывает на директорию исходной модели."""
        src = self.mapToSource(index)
        model = self.sourceModel()
        return isinstance(model, QFileSystemModel) and model.isDir(src)

    def _has_checked_dir_ancestor(self, index: QModelIndex) -> bool:
        """
        Вернуть True, если у элемента есть отмеченный checkbox предок-директория.
        Используется для визуальной деактивации и запрета изменений у потомков.
        """
        p = index.parent()
        while p.isValid():
            if self._is_dir(p):
                if (
                        self._checks.get(self._path(p), Qt.CheckState.Unchecked)
                        == Qt.CheckState.Checked
                ):
                    return True
            p = p.parent()
        return False

    # ===== Переопределения модели =====

    def data(
            self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)
    ) -> Any:
        """
        Возвращает данные для ролей:
        - CheckStateRole: состояние чекбокса для колонки 0.
        - ForegroundRole: серый, если у элемента есть отмеченный предок;
                          тёмно-синий для колонки 0, если элемент сам отмечен.
        Остальные роли — из базовой реализации.
        """
        path = self._path(index)

        # Состояние чекбокса отображаем только в первой колонке
        if role == int(Qt.ItemDataRole.CheckStateRole) and index.column() == 0:
            return self._checks.get(path, Qt.CheckState.Unchecked)

        # Цвет текста
        if role == int(Qt.ItemDataRole.ForegroundRole):
            # Серый для всех колонок, если есть отмеченный предок
            if self._has_checked_dir_ancestor(index):
                return QBrush(Qt.GlobalColor.gray)
            # Тёмно-синий только для колонки 0, если сам отмечен
            if (
                    index.column() == 0
                    and self._checks.get(path, Qt.CheckState.Unchecked)
                    == Qt.CheckState.Checked
            ):
                return QBrush(Qt.GlobalColor.darkBlue)

        return super().data(index, role)

    def flags(self, index: QModelIndex):
        """
        Добавляет флаг чекбокса для колонки 0.
        Если у элемента есть отмеченный предок-директория, снимает возможность
        редактирования и пользовательской установки чекбокса.
        """
        f = super().flags(index)
        if index.column() == 0:
            f |= Qt.ItemFlag.ItemIsUserCheckable
            if self._has_checked_dir_ancestor(index):
                f &= ~Qt.ItemFlag.ItemIsEnabled
                f &= ~Qt.ItemFlag.ItemIsUserCheckable
        return f

    def setData(
            self,
            index: QModelIndex,
            value: object,
            role: int = int(Qt.ItemDataRole.EditRole),
    ) -> bool:
        """
        Обрабатывает клики по checkbox:
        - Запрещает изменение, если у элемента есть отмеченный предок-директория.
        - Сохраняет состояние в self._checks (удаляет ключ при Unchecked).
        - Посылает сигнал dataChanged для всего дерева, чтобы обновить цвета и флаги.
        """
        if role == int(Qt.ItemDataRole.CheckStateRole) and index.column() == 0:
            if self._has_checked_dir_ancestor(index):
                return False
            path = self._path(index)
            state = Qt.CheckState(value)  # type: ignore[arg-type]
            if state == Qt.CheckState.Unchecked:
                self._checks.pop(path, None)
            else:
                self._checks[path] = state
            # Грубое оповещение всего дерева: просто и достаточно для масштабов примера
            self.dataChanged.emit(
                QModelIndex(),
                QModelIndex(),
                [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole],
            )
            return True
        return super().setData(index, value, role)

    def checked_paths(self) -> list[str]:
        """Список путей, отмеченных пользователем."""
        return [p for p, st in self._checks.items() if st == Qt.CheckState.Checked]


class MainWindow(QMainWindow):
    """
    Главное окно с QTreeView и тремя кнопками управления.
    UI загружается из 'tree_with_checkboxes.ui'.
    """

    # Аннотации для атрибутов, создаваемых через loadUi
    treeView: QTreeView
    btnSelectAll: QPushButton
    btnClearAll: QPushButton
    btnShow: QPushButton

    def __init__(self):
        super().__init__()
        # Загружаем сгенерированный в Qt Designer .ui
        uic.loadUi("tree_with_checkboxes.ui", self)

        # Исходная модель файловой системы
        fs = QFileSystemModel(self)
        fs.setRootPath("")  # Windows: список дисков; Unix: '/'
        fs.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        # Оборачиваем в прокси с checkboxes и правилами блокировки/подсветки
        self.model = CheckableFSModel(self)
        self.model.setSourceModel(fs)

        # Древовидное представление
        self.treeView.setModel(self.model)
        # Показать всю файловую систему (корень)
        self.treeView.setRootIndex(self.model.mapFromSource(fs.index("")))
        self.treeView.setColumnWidth(0, 320)
        self.treeView.setSortingEnabled(True)

        # Сигналы кнопок
        self.btnSelectAll.clicked.connect(self.select_all_visible)
        self.btnClearAll.clicked.connect(self.clear_all)
        self.btnShow.clicked.connect(self.show_checked)

    # ===== Обработчики кнопок =====

    def select_all_visible(self):
        """
        Простой пример «отметить видимые»: пробегаем по первой странице потомков
        текущего корня модели и ставим checkboxes. В реальном приложении лучше
        обходить по видимым индексам/рекурсивно.
        """
        v = self.treeView
        top = v.indexAt(v.viewport().rect().topLeft())
        if not top.isValid():
            return
        rows = self.model.rowCount(self.model.index(0, 0).parent())
        for r in range(rows):
            idx = self.model.index(r, 0)
            self.model.setData(
                idx, Qt.CheckState.Checked, int(Qt.ItemDataRole.CheckStateRole)
            )

    def clear_all(self):
        """Снять все отметки и обновить представление."""
        # noinspection PyProtectedMember
        self.model._checks.clear()
        self.model.dataChanged.emit(
            QModelIndex(),
            QModelIndex(),
            [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole],
        )

    def show_checked(self):
        """Вывести в stdout перечень отмеченных путей."""
        print("Отмечены:")
        for p in self.model.checked_paths():
            print(" -", p)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(900, 600)
    w.show()
    sys.exit(app.exec())
