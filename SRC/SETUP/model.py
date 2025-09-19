"""
Прокси-модель файловой системы с флажками поверх QFileSystemModel.

Возможности:
  • Хранение и загрузка отмеченных путей в JSON.
  • Визуальные состояния флажков: Checked / PartiallyChecked / Unchecked.
  • Корректная рассылка dataChanged вверх/вниз по ветке.
  • Автоматическое раскрытие корневых узлов, если внутри есть отмеченные элементы.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QDir, QModelIndex, QIdentityProxyModel
from PyQt6.QtGui import QBrush, QFileSystemModel, QFont

import SRC.SETUP.utils as utils


class CheckableFSModel(QIdentityProxyModel):
    """Прокси над QFileSystemModel с флажками в первой колонке.

    Поведение:
        • Если путь явно есть в self.checks:
            – состояние: Checked
            – цвет текста: тёмно-синий
        • Если предок отмечен, но сам путь не в self.checks:
            – состояние: Checked
            – цвет текста: серый (визуально показывает, что отметка унаследована)
        • Если директория не отмечена, но имеет отмеченные потомки:
            – состояние: PartiallyChecked
            – цвет текста: обычный
        • Если директория и все потомки сняты:
            – состояние: Unchecked
            – цвет текста: обычный

    Хранилище:
        self.checks — множество нормализованных абсолютных путей,
        которые пользователь отметил явно (ставил или снимал флажок).
    """

    # Инициализация модели

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Загружаем ранее отмеченные пути файлов/директорий из файла и нормализуем до единого вида
        self.checks: set[str] = self.get_checks()

    def get_checks(self) -> set[str]:
        existing, deleted = utils.load_set_json()
        return {self._norm(p) for p in existing}

    def root_for_all_drives(self, fs) -> QModelIndex:
        """
        Возвращает корневой индекс модели для всех дисков.

        Аргументы:
            fs (QFileSystemModel): исходная файловая модель, от которой берётся индекс "".

        Возврат:
            QModelIndex: индекс корневого узла, отображающий весь список дисков.
        """

        return self.mapFromSource(fs.index(""))

    def iter_marked_top(self):
        """
        Генератор для обхода отмеченных корневых элементов.

        Логика:
            • Просматривает верхний уровень модели (список дисков).
            • Проверяет состояние чекбокса каждого элемента.
            • Возвращает индексы с состоянием Checked или PartiallyChecked.

        Возврат:
            Iterator[QModelIndex]: индексы отмеченных корневых элементов.
        """
        root = QModelIndex()
        for r in range(self.rowCount(root)):
            idx = self.index(r, 0, root)
            state = self.data(idx, Qt.ItemDataRole.CheckStateRole)
            if state in (Qt.CheckState.Checked, Qt.CheckState.PartiallyChecked):
                yield idx

    def _emit_branch_changed(self, index: QModelIndex) -> None:
        """Обновляет предков узла для перерасчёта Partial.

        Рассылает dataChanged предкам, чтобы пересчитать CheckState/Foreground

        Args:
            index: Точка старта.
        """
        it = index
        while it.isValid():
            parent = it.parent()
            if parent.isValid():
                self.dataChanged.emit(
                    parent,
                    parent,
                    [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole],
                )
            it = parent

    def _emit_subtree_changed(self, parent: QModelIndex) -> None:
        """Рассылает сигналы dataChanged для всего поддерева начиная с parent.

        Рекурсивно обходит все узлы, чтобы делегат пересчитал состояние флажков
        и цвета текста.

            Тест на дереве ~5000 узлов показал мгновенную реакцию,
            поэтому производительность приемлема.


        Args:
            parent: Корень поддерева.

        Notes:
            Может затронуть большое число узлов на больших деревьях.
        """
        rows, cols = self.rowCount(parent), self.columnCount(parent)
        if rows > 0 and cols > 0:
            self._emit_range_changed(
                parent
            )  # Сигнал обновления для всех ячеек родителя
            self._recurse_children(
                parent
            )  # Рекурсивно обходим все строки и обновляем их поддеревья

    def _emit_range_changed(self, parent: QModelIndex) -> None:
        """Шлёт сигнал dataChanged для всех ячеек в пределах parent.

        Обновляет состояния флажков и цвета текста у прямых потомков parent.
        """
        rows, cols = self.rowCount(parent), self.columnCount(parent)
        if rows and cols:
            tl = self.index(0, 0, parent)
            br = self.index(rows - 1, cols - 1, parent)
            self.dataChanged.emit(
                tl, br, [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole]
            )

    def _recurse_children(self, parent: QModelIndex) -> None:
        """Обходит потомков и инициирует обновление их поддеревьев.

        Нужен, чтобы корректно обновить состояние флажков на всех уровнях.
        """
        for r in range(self.rowCount(parent)):
            self._emit_subtree_changed(self.index(r, 0, parent))

    def _norm(self, p: str) -> str:
        """Нормализует путь с помощью QDir.cleanPath (нативные разделители ОС)."""

        return QDir.cleanPath(p)

    def _is_dir(self, index: QModelIndex) -> bool:
        """Проверяет, что индекс указывает на директорию,
        чтобы корректно применять логику наследования отметок."""

        src = self.mapToSource(index)
        model = self.sourceModel()
        return isinstance(model, QFileSystemModel) and model.isDir(src)

    def _path(self, index: QModelIndex) -> str:
        """Возвращает нормализованный абсолютный путь для индекса или пустую строку."""

        src = self.mapToSource(index)
        model = self.sourceModel()
        if isinstance(model, QFileSystemModel):
            return self._norm(model.filePath(src))
        return ""

    def _has_marked_descendant(self, dir_path: str) -> bool:
        """Проверяет наличие отмеченного потомка у директории.

        Сравнение по префиксу 'base/' исключает ложные совпадения типа
        '/foo' vs '/foobar' и саму базовую папку.
        """

        base = self._norm(dir_path).rstrip("/")
        if not base:
            return False
        prefix = base + "/"  # добавляем '/' чтобы исключить ложные префиксы
        for p in self.checks:
            # p.startswith(prefix) — строго поддерево; p != base исключает саму папку
            if p != base and p.startswith(prefix):
                return True
        return False

    def _has_checked_dir_ancestor(self, index: QModelIndex) -> bool:
        """Проверяет, есть ли среди предков явная отметка директории."""

        # Поднимаемся по дереву и проверяем каждый путь в self.checks
        it = index.parent()
        while it.isValid():
            if self._path(it) in self.checks:
                return True
            it = it.parent()
        return False

    # --- помощники для data ---

    def _check_state(self, index: QModelIndex) -> Qt.CheckState:
        """Возвращает Qt.CheckState для первой колонки."""
        path = self._path(index)

        if self._is_explicitly_checked(path):
            return Qt.CheckState.Checked

        if self._is_inherited_checked(index):
            return Qt.CheckState.Checked

        if self._is_partially_checked(index, path):
            return Qt.CheckState.PartiallyChecked

        return Qt.CheckState.Unchecked

    def _foreground(self, index: QModelIndex) -> QBrush | None:
        """Цвет текста: тёмно-синий для явной отметки, серый для унаследованной."""
        path = self._path(index)

        if self._is_explicitly_checked(path):
            return QBrush(Qt.GlobalColor.darkBlue)

        if self._is_inherited_checked(index):
            return QBrush(Qt.GlobalColor.gray)

        return None

    def _is_explicitly_checked(self, path: str) -> bool:
        """Путь явно отмечён пользователем."""
        return path in self.checks

    def _is_inherited_checked(self, index: QModelIndex) -> bool:
        """Отметка унаследована от отмеченного предка."""
        return self._has_checked_dir_ancestor(index)

    def _is_partially_checked(self, index: QModelIndex, path: str) -> bool:
        """Директория не отмечена, но имеет отмеченных потомков."""
        return self._is_dir(index) and self._has_marked_descendant(path)

    def _font(self, index: QModelIndex) -> QFont | None:
        """Возвращает жирный шрифт для явно отмеченных элементов."""
        if self._is_explicitly_checked(self._path(index)):
            f = QFont()
            f.setBold(True)
            return f
        return None

    # ----- Помощник для setData

    def _apply_check(self, path: str, state: Qt.CheckState) -> None:
        """Обновляет self.checks: добавляет путь в множество отмеченных элементов при Checked, иначе удаляет."""
        if state == Qt.CheckState.Checked:
            self.checks.add(path)
        else:
            self.checks.discard(path)

    # ----- Обработка флагов

    def flags(self, index) -> Qt.ItemFlag:
        """Возвращает флаги элемента.

        • Для элементов, состояние которых унаследовано от предка,
          флажки отображается, но попытки изменить состояние игнорируются.
        • Для остальных элементы доступны, выбираемы и с активным флажками.

        Returns:
            Qt.ItemFlags: Битовое сочетание флагов.
        """
        fl = super().flags(index)
        if self._has_checked_dir_ancestor(index):
            # Если родитель уже помечен — запрещаем выбор и изменение флажка
            fl &= ~Qt.ItemFlag.ItemIsEnabled
            fl &= ~Qt.ItemFlag.ItemIsUserCheckable
        else:
            # Разрешаем выбор и работу с флажками
            fl |= (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
        return fl

    # ----- возвращает данные по индексу и роли

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """Возвращает данные для делегата.

        Roles:
            CheckStateRole (колонка 0):
                • Checked — явная отметка или наследование от отмеченного предка.
                • PartiallyChecked — директория с отмеченными потомками.
                • Unchecked — иначе.
            ForegroundRole:
                • darkBlue — явная отметка.
                • gray — наследование от предка.

        Прочие роли делегируются базовой реализации.
        """

        # Обрабатываем только валидные индексы
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            return self._check_state(index)

        if role == Qt.ItemDataRole.ForegroundRole:
            fg = self._foreground(index)
            if fg is not None:
                return fg

        if role == Qt.ItemDataRole.FontRole:
            f = self._font(index)
            if f is not None:
                return f

        return super().data(index, role)

    # ----- записывает данные по индексу и роли

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        """Обрабатывает изменение состояния флажка в первой колонке.

        Args:
            index: Элемент дерева
            value: Новое значение (Qt.CheckState)
            role: Тип роли, по умолчанию EditRole

        Returns:
            True, если состояние изменено и сигналы разосланы.
        """
        if (
            role != Qt.ItemDataRole.CheckStateRole
            or index.column() != 0
            or not index.isValid()
        ):
            return super().setData(index, value, role)

        # Игнорируем клик по унаследованным (серым) элементам
        if self._has_checked_dir_ancestor(index):
            return False

        path = self._path(index)
        state = Qt.CheckState(value)
        self._apply_check(path, state)

        # Рассылка обновлений вниз и вверх
        self._emit_subtree_changed(index)  # вниз — чтобы дети перерисовались
        self._emit_branch_changed(index)  # вверх — чтобы родители пересчитали Partial
        return True
