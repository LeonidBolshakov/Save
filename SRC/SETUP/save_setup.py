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

Зависимости: PyQt6, model.CheckableFSModel, utils (COL0_WIDTH, INIT_DELAY_MS, save_set_to_file, UserAbort).

Запуск: python save_setup.py
"""

from __future__ import annotations

import sys

from PyQt6 import uic
from PyQt6.QtCore import QDir, QTimer
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView, QCheckBox

from SRC.SETUP.model import CheckableFSModel
from SRC.SETUP.schedulepanel import SchedulePanel
from SRC.SETUP.legendwidwets import Legend
from SRC.GENERAL import paths_win
import SRC.SETUP.utils as utils


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

        ui_file = paths_win.resource_path("save_setup.ui")
        uic.loadUi(ui_file, self)
        utils.setup_logging()

        self.legend = Legend(self)
        self.legend.init_legend()
        paths_win.ensure_env_exists()
        self.schedule = SchedulePanel(self)

        fs = self.create_source_model()  # Исходная модель
        self.model = self.create_proxy_model(
            fs
        )  # Оборачиваем в прокси с флажками и наследованием отметок и окраски текста
        self.init_view(fs)

    def create_source_model(self) -> QFileSystemModel:
        """Создаёт и настраивает исходную модель файловой системы."""
        fs = QFileSystemModel(self)
        fs.setRootPath("")  # Windows: список дисков
        fs.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        return fs

    def create_proxy_model(self, fs: QFileSystemModel) -> CheckableFSModel:
        """Создаёт прокси-модель с флажками и наследованием отметок."""
        model = CheckableFSModel()
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
        self.treeView.setRootIndex(self.model.root_for_all_drives(fs))
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
        list_archive_file_paths = paths_win.get_list_archive_file_paths()

        utils.save_set_to_file(self.model.checks, list_archive_file_paths)

    def _expand_marked_disks(self) -> None:
        """
        Раскрывает в дереве отмеченные диски.

        Действия:
            • Получает список индексов корневых элементов с установленным чекбоксом.
            • Для каждого индекса вызывает setExpanded(True) в treeView.
        """
        for idx in self.model.iter_marked_top():
            self.treeView.setExpanded(idx, True)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        w = MainWindow()
        w.show()
        return_code = app.exec()

        sys.exit(return_code)
    except utils.UserAbort:
        sys.exit(130)
