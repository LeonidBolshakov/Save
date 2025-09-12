# -*- coding: utf-8 -*-
"""
Комментированные фрагменты для вашей модели на базе QIdentityProxyModel.
Включает:
  1) Сохранение/загрузка множества путей в JSON.
  2) Подсветка и чекбоксы: Checked / PartiallyChecked / Unchecked.
  3) Корректная рассылка dataChanged по ветке при клике.

Примечание:
- Оставлены явные комментарии «что» и «почему» почти к каждой строке.
- Импорт и имена согласованы с PyQt6.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QDir, QModelIndex, QIdentityProxyModel
from PyQt6.QtGui import QBrush, QFileSystemModel
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView


# ---------------------------------------------------------------------------
# 1) УТИЛИТЫ: сохранить/загрузить МНОЖЕСТВО путей как JSON-список
# ---------------------------------------------------------------------------


def save_set_json(items: set[str], path: str | Path = "marked elements.json") -> None:
    """Сохранить множество строк в JSON-список.
    Сортировка даёт детерминированный порядок строк в файле.
    """
    p = Path(path)
    # ensure_ascii=False — кириллица пишется «как есть» в UTF‑8.
    with p.open("w", encoding="utf-8") as f:
        json.dump(sorted(items), f, ensure_ascii=False, indent=2)


def load_set_json(path: str | Path = "marked elements.json") -> set[str]:
    """Загрузить множество строк из JSON-списка. Пустой файл → пустое множество.
    Ошибки парсинга гасим и возвращаем пустое множество, чтобы не падать при старте.
    """
    p = Path(path)
    if not p.exists():
        return set()
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)  # читаем ОДИН раз
        # Ожидаем список строк; неподходящие элементы отфильтруем
        return {str(x) for x in data}
    except json.JSONDecodeError:
        # Битый/обрезанный JSON — считаем, что пока нет сохранённых отметок
        return set()


# ---------------------------------------------------------------------------
# 2) ПРОКСИ-МОДЕЛЬ: визуализация Checked / PartiallyChecked без изменения self.checks
# ---------------------------------------------------------------------------


class CheckableFSModel(QIdentityProxyModel):
    """Прокси над QFileSystemModel с чекбоксами в колонке 0

    self.checks: set[str] — набор ПОЛНЫХ путей, которые пользователь явно отметил.
    Визуально:
      - Если путь в self.checks → Checked.
      - Если путь — директория и в self.checks есть её потомки → PartiallyChecked.
      - Иначе → Unchecked.
    При этом «серые» галки считаются вычислёнными и в self.checks НЕ пишутся.
    """

    # -----------------------
    # ИНИЦИАЛИЗАЦИЯ МОДЕЛИ
    # -----------------------

    def __init__(self, parent=None):
        super().__init__(parent)
        # Загружаем отмеченные пути из файла и нормализуем до единого вида
        self.checks: set[str] = {self._norm(p) for p in load_set_json()}

    # -----------------------
    # ПОМОЩНИКИ ДЛЯ ПУТЕЙ
    # -----------------------

    def _norm(self, p: str) -> str:
        """Нормализовать путь: убрать ./.., привести разделители к '/'.
        Это упрощает сравнение путей как строк.
        """
        return QDir.cleanPath(p).replace("\\", "/")

    def _is_dir(self, index: QModelIndex) -> bool:
        """Проверить, что индекс — директория в исходной QFileSystemModel."""
        src = self.mapToSource(index)
        model = self.sourceModel()
        return isinstance(model, QFileSystemModel) and model.isDir(src)

    def _path(self, index: QModelIndex) -> str:
        """Получить нормализованный абсолютный путь у индекса из исходной модели."""
        src = self.mapToSource(index)
        model = self.sourceModel()
        if isinstance(model, QFileSystemModel):
            return self._norm(model.filePath(src))
        return ""

    # -----------------------
    # ПРОВЕРКА РОДСТВА ПУТЕЙ
    # -----------------------

    def _has_marked_descendant(self, dir_path: str) -> bool:
        """Есть ли среди self.checks потомок указанной директории.
        Сравнение по префиксу строки безопасно, т.к. все пути нормализованы и
        добавляем разделитель, чтобы /foo не считал /foobar потомком.
        """
        base = self._norm(dir_path).rstrip("/")
        if not base:
            return False
        prefix = base + "/"
        for p in self.checks:
            # p.startswith(prefix) — строго поддерево; p != base исключает саму папку
            if p != base and p.startswith(prefix):
                return True
        return False

    def _has_checked_dir_ancestor(self, index: QModelIndex) -> bool:
        """Есть ли среди предков текущего индекса директория, уже отмеченная как Checked.
        Нужна, если по вашей логике дети «наследуют» заливку/цвет и должны игнорировать клики.
        Если наследование не требуется — можно не использовать.
        """
        # Поднимаемся по дереву и проверяем каждый путь в self.checks
        it = index.parent()
        while it.isValid():
            if self._path(it) in self.checks:
                return True
            it = it.parent()
        return False

    # -----------------------
    # data(): отдаём состояния чекбокса и цвета
    # -----------------------

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        # Обрабатываем только валидные индексы
        if not index.isValid():
            return super().data(index, role)

        # ЧЕКБОКСЫ рисуются делегатом только если модель возвращает состояние
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            path = self._path(index)

            # 1) Явная отметка пользователя
            if path in self.checks:
                return Qt.CheckState.Checked

            # 2) у предков есть явная отметка → показываем галку, но это не «ручная»
            if self._has_checked_dir_ancestor(index):
                return Qt.CheckState.Checked

            # 3) частично: есть помеченные потомки
            if self._is_dir(index) and self._has_marked_descendant(path):
                return Qt.CheckState.PartiallyChecked

            # 4) По умолчанию нет галки
            return Qt.CheckState.Unchecked

        # Цветовое оформление
        if role == Qt.ItemDataRole.ForegroundRole and index.column() == 0:
            path = self._path(index)

            # явная отметка - тёмно-синий
            if path in self.checks:
                return QBrush(Qt.GlobalColor.darkBlue)

            # наследованная от родителя — серый
            if self._has_checked_dir_ancestor(index):
                return QBrush(Qt.GlobalColor.gray)

        # Остальное — базовая реализация
        return super().data(index, role)

    def flags(self, index):
        fl = super().flags(index)
        if self._has_checked_dir_ancestor(index):
            fl &= ~Qt.ItemFlag.ItemIsEnabled
            fl &= ~Qt.ItemFlag.ItemIsUserCheckable
        else:
            fl |= (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
        return fl

    # -----------------------
    # setData(): обработка клика по чекбоксу
    # -----------------------

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        # Интересуют только чекбоксы колонки 0
        if (
            role != Qt.ItemDataRole.CheckStateRole
            or index.column() != 0
            or not index.isValid()
        ):
            return super().setData(index, value, role)

        # По желанию можно запретить клик по «унаследованным» элементам
        if self._has_checked_dir_ancestor(index):
            return False

        # Вычисляем, что именно хотим записать в self.checks
        path = self._path(index)
        state = Qt.CheckState(value)

        if state == Qt.CheckState.Checked:
            # Явная отметка → добавляем путь
            self.checks.add(path)
        else:
            # Unchecked или PartiallyChecked → снимаем явную отметку
            # (Partially здесь трактуем как снятие явной отметки у узла)
            self.checks.discard(path)

        # Обновляем ветку: родителя, самого индекса и соседей под тем же родителем
        self._emit_subtree_changed(index)  # вниз — чтобы дети перерисовались
        self._emit_branch_changed(index)  # вверх — чтобы родители пересчитали Partial
        return True

    # -----------------------
    # Рассылка обновлений: корректно и адресно
    # -----------------------

    def _emit_branch_changed(self, index: QModelIndex) -> None:
        """Поднимаемся по ветке и для каждого родителя шлём dataChanged по всем детям.
        Это дешёвый способ «пересчитать» PartiallyChecked на пути к корню.
        """
        it = index
        while it.isValid():
            parent = it.parent()
            rows = self.rowCount(parent)
            cols = self.columnCount(parent)
            if rows > 0 and cols > 0:
                # Диапазон в рамках одного родителя обязателен для dataChanged
                top_left = self.index(0, 0, parent)
                bottom_right = self.index(rows - 1, cols - 1, parent)
                self.dataChanged.emit(
                    top_left,
                    bottom_right,
                    [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole],
                )
            it = parent

    def _emit_subtree_changed(self, parent: QModelIndex) -> None:
        rows, cols = self.rowCount(parent), self.columnCount(parent)
        if rows > 0 and cols > 0:
            tl = self.index(0, 0, parent)
            br = self.index(rows - 1, cols - 1, parent)
            self.dataChanged.emit(
                tl, br, [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole]
            )
            for r in range(rows):
                self._emit_subtree_changed(self.index(r, 0, parent))


# ---------------------------------------------------------------------------
# 3) ПРИМЕР closeEvent: сохранить набор перед закрытием окна (по месту вызова)
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    """
    Главное окно с QTreeView и тремя кнопками управления.
    UI загружается из 'tree_with_checkboxes.ui'.
    """

    # Аннотации для атрибутов, создаваемых через loadUi
    treeView: QTreeView

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

    def closeEvent(self, e) -> list[str]:
        """Запомнить перечень отмеченных путей."""
        self.save_checks()
        e.accept()

    def save_checks(self) -> None:
        try:
            with open("marked elements.json", "w", encoding="utf-8") as f:
                json.dump(sorted(self.model.checks), f, ensure_ascii=False, indent=2)
        except Exception as err:
            raise IOError(err)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return_code = app.exec()

    sys.exit(return_code)
