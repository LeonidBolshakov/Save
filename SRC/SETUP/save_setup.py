"""save_setup.py — главный модуль приложения с окном и деревом файлов.

Назначение:
  • Загрузка UI из 'save_setup.ui'.
  • Настройка QFileSystemModel с фильтром QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot.
  • Обёртка модели в CheckableFSModel.
  • Инициализация QTreeView и отложенное раскрытие помеченных узлов.
  • Сохранение отметок при закрытии окна.

Состав:
  • class MainWindow.
  • Точка входа: if __name__ == "__main__".

Зависимости: PyQt6, model.CheckableFSModel, utils (COL0_WIDTH, INIT_DELAY_MS, save_set_json, UserAbort).

Запуск: python save_setup.py
"""

from __future__ import annotations

import sys

from PyQt6 import uic, QtCore
from PyQt6.QtCore import (
    QDir,
    QModelIndex,
    QTimer,
    Qt,
)
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView, QCheckBox

from model import CheckableFSModel
import utils


class MainWindow(QMainWindow):
    """Главное окно приложения для отметки файлов и каталогов.

    Задачи:
    - загрузка интерфейса из 'save_setup.ui';
    - создание и настройка QFileSystemModel с фильтром AllEntries | NoDotAndDotDot;
    - обёртка источника в CheckableFSModel и привязка к QTreeView;
    - первичная настройка представления (root index, ширина колонки, сортировка);
    - отложенное раскрытие помеченных узлов;
    - сохранение отмеченных путей при закрытии.

    Атрибуты:
        treeView (QTreeView): виджет дерева из .ui
        model (CheckableFSModel): прокси-модель с флажками"""

    # Аннотации для атрибутов, создаваемых через loadUi
    treeView: QTreeView
    checkBox_no_select: QCheckBox
    checkBox_partially_select: QCheckBox
    checkBox_select: QCheckBox
    checkBox_auto_select: QCheckBox

    def __init__(self):
        super().__init__()
        uic.loadUi("save_setup.ui", self)
        self._init_legend()

        fs = self.create_source_model()  # Исходная модель
        self.model = self.create_proxy_model(
            fs
        )  # Оборачиваем в прокси с флажками и наследование отметок и окраска текста
        self.init_view(fs)

    def _init_legend(self):
        # Устанавливаем чекбоксу неопределенное состояние
        self.checkBox_partially_select.setCheckState(
            QtCore.Qt.CheckState.PartiallyChecked
        )
        # Блокируем нажатия по клику флажков легенды
        self.checkBox_partially_select.stateChanged.connect(self.ignore_state_change)
        self.checkBox_select.stateChanged.connect(self.ignore_state_change)

    def ignore_state_change(self):
        self.checkBox_partially_select.setCheckState(
            QtCore.Qt.CheckState.PartiallyChecked
        )
        self.checkBox_select.setCheckState(QtCore.Qt.CheckState.Checked)

    def create_source_model(self) -> QFileSystemModel:
        """Создаёт и настраивает исходную модель файловой системы."""
        fs = QFileSystemModel(self)
        fs.setRootPath("")  # Windows: список дисков; Unix: '/'
        fs.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        return fs

    def create_proxy_model(self, fs: QFileSystemModel) -> CheckableFSModel:
        """Создаёт прокси-модель с флажками и наследованием отметок."""
        model = CheckableFSModel(self)
        model.setSourceModel(fs)
        return model

    def init_view(self, fs: QFileSystemModel) -> None:
        """Инициализирует дерево файлов.

        Действия:
            • Подключает модель к treeView.
            • Устанавливает корневой индекс на весь диск/список дисков.
            • Настраивает ширину первой колонки и сортировку.
            • Планирует отложенное раскрытие помеченных дисков
              после загрузки содержимого модели.
        """

        self.treeView.setModel(self.model)
        self.treeView.setRootIndex(self.model.mapFromSource(fs.index("")))
        self.treeView.setColumnWidth(0, utils.COL0_WIDTH)
        self.treeView.setSortingEnabled(True)
        QTimer.singleShot(
            utils.INIT_DELAY_MS, self._expand_marked_disks
        )  # Отложенный вызов: ждём, пока QFileSystemModel загрузит корневой уровень.

    def closeEvent(self, e) -> None:
        """Сохраняет текущие отметки перед закрытием окна и принимает событие."""
        self.save_checks()
        e.accept()

    def save_checks(self) -> None:
        """Сохраняет self.model.checks"""

        utils.save_set_json(self.model.checks, "marked elements.json")

    def _expand_marked_disks(self) -> None:
        """Раскрывает корневые узлы, помеченные Checked/PartiallyChecked.

        Использует пустой QModelIndex как безопасный корень, так как rootIndex()
        может быть ещё не инициализирован на момент вызова.
        """
        root = QModelIndex()
        rows = self.model.rowCount(root)
        for r in range(rows):
            idx = self.model.index(r, 0, root)
            if not idx.isValid():
                continue
            state = self.model.data(idx, Qt.ItemDataRole.CheckStateRole)
            if state in (Qt.CheckState.PartiallyChecked, Qt.CheckState.Checked):
                self.treeView.setExpanded(idx, True)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        w = MainWindow()
        w.show()
        return_code = app.exec()

        sys.exit(return_code)
    except utils.UserAbort:
        sys.exit(130)
