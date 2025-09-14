"""
Прокси-модель файловой системы с флажками поверх QFileSystemModel.

Возможности:
  • Хранение и загрузка отмеченных путей в JSON.
  • Визуальные состояния флажков: Checked / PartiallyChecked / Unchecked.
  • Корректная рассылка dataChanged вверх/вниз по ветке.
  • Автоматическое раскрытие корневых узлов, если внутри есть отмеченные элементы.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtCore import Qt, QDir, QModelIndex, QIdentityProxyModel, QTimer
from PyQt6.QtGui import QBrush, QFileSystemModel, QFont
from PyQt6.QtWidgets import QApplication, QMainWindow, QTreeView

ERROR_TEXT = (
    "Файла с пометками сохраняемых файлов/каталогов {p} не обнаружен.\n"  # 0
    "Начинаем работу 'с чистого листа'",
    "Нарушена структура файла с пометками сохраняемых файлов/каталогов {p}\n"  # 1
    "{e}\n"
    "Считаем что такого файла нет",
    "Нет доступа к файлу с пометками сохраняемых файлов/каталогов {p}\n"  # 2
    "{e}\n"
    "Считаем что такого файла нет",
    "Не могу сохранить информацию об отмеченных файлах/каталогах. Нет доступа к файлу {p}\n"  # 3
    "{e}\n",
    "Не могу сохранить информацию об отмеченных файлах/каталогах. Ошибка вывода {p}\n"  # 4
    "{e}\n",
)
INIT_DELAY_MS = 100
COL0_WIDTH = 320


# ----- 1. УТИЛИТЫ: сохранить/загрузить МНОЖЕСТВО путей как JSON-список и вспомогательные функции.


def save_set_json(items: set[str], path: str | Path = "marked elements.json") -> None:
    """Сохраняет множество путей в JSON-файл.

    Порядок в файле детерминирован (предварительная сортировка).

    Args:
        items: Множество полных путей отмеченных элементов
        path: Путь к JSON-файлу.

    Raises:
        PermissionError: Нет доступа к каталогу/файлу.
        OSError: Ошибка ввода-вывода при создании каталога или записи файла.
    """
    p = Path(path)

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        error_message(3, p, e)
    except OSError as e:
        error_message(4, p, e)

    try:
        # ensure_ascii=False — кириллица пишется «как есть» в UTF‑8.
        with p.open("w", encoding="utf-8") as f:
            json.dump(sorted(items), f, ensure_ascii=False, indent=2)
    except PermissionError as e:
        error_message(3, p, e)
    except OSError as e:
        error_message(4, p, e)


def get_set_marked_files(p: Path) -> set[str]:
    """Читает JSON и возвращает множество путей.

    Args:
        p: Путь к JSON-файлу.

    Returns:
        Множество строковых путей.

    Raises:
        FileNotFoundError: Файл отсутствует.
        UnicodeDecodeError | json.JSONDecodeError | ValueError: Повреждён или не-JSON.
        PermissionError | OSError: Проблемы доступа/ввода-вывода.
    """
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(x) for x in data}


def error_message(error_number: int, p: Path, e: Exception | None = None) -> None:
    """Выводит диагностическое сообщение.

    Args:
        error_number: Индекс шаблона сообщения в ERROR_TEXT
        p: Путь файла/директории, фигурирующий в сообщении
        e: Первопричина (если есть)

    Returns:
        None
    """

    print(ERROR_TEXT[error_number].format(p=p, e=str(e) if e else ""))


def load_set_json(path: str | Path = "marked elements.json") -> set[str]:
    """Загружает множество путей из JSON.

    Отсутствие файла и ошибки парсинга трактуются как «нет данных»,
    функция возвращает пустое множество и печатает диагностику.

    Args:
        path: Путь к JSON-файлу.

    Returns:
        Множество путей (возможно пустое).
    """
    p = Path(path)

    try:
        return get_set_marked_files(p)
    except FileNotFoundError:
        error_message(0, p)
        return set()
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as e:
        error_message(1, p, e)
        return set()
    except PermissionError as e:
        error_message(2, p, e)
        return set()


# ----- 2. ПРОКСИ-МОДЕЛЬ: визуализация Checked / PartiallyChecked без изменения self.checks


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
        # Загружаем отмеченные пути файлов/директорий из файла и нормализуем до единого вида
        self.checks: set[str] = self.get_checks()

    def get_checks(self) -> set[str]:
        return {self._norm(p) for p in load_set_json()}

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

    def _apply_check(self, path: str, state: Qt.CheckState) -> None:
        """Обновляет self.checks: добавляет путь в множество отмеченных элементов при Checked, иначе удаляет."""
        if state == Qt.CheckState.Checked:
            self.checks.add(path)
        else:
            self.checks.discard(path)

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        # noinspection GrazieInspection
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

        # Запрещаем клик по унаследованным (серым) элементам
        if self._has_checked_dir_ancestor(index):
            return False

        path = self._path(index)
        state = Qt.CheckState(value)
        self._apply_check(path, state)

        # Рассылка обновлений вниз и вверх
        self._emit_subtree_changed(index)  # вниз — чтобы дети перерисовались
        self._emit_branch_changed(index)  # вверх — чтобы родители пересчитали Partial
        return True


# ----- 3. Главное окно программы


class MainWindow(QMainWindow):
    """Главное окно с QTreeView.

    Загружает UI из 'tree_with_checkboxes.ui', настраивает QFileSystemModel
    и оборачивает её в CheckableFSModel. После инициализации раскрывает
    корневые узлы, где обнаружены помеченные элементы.
    """

    # Аннотации для атрибутов, создаваемых через loadUi
    treeView: QTreeView

    def __init__(self):
        super().__init__()
        uic.loadUi("tree_with_checkboxes.ui", self)

        fs = self.create_source_model()  # Исходная модель
        self.model = self.create_proxy_model(
            fs
        )  # Оборачиваем в прокси с флажками и наследование отметок и окраска текста
        self.init_view(fs)

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
        self.treeView.setColumnWidth(0, COL0_WIDTH)
        self.treeView.setSortingEnabled(True)
        QTimer.singleShot(
            INIT_DELAY_MS, self._expand_marked_disks
        )  # Отложенный вызов: ждём, пока QFileSystemModel загрузит корневой уровень.

    def closeEvent(self, e) -> None:
        """Сохраняет текущие отметки перед закрытием окна и принимает событие."""
        self.save_checks()
        e.accept()

    def save_checks(self) -> None:
        """Сохраняет self.model.checks в 'marked elements.json'."""

        save_set_json(self.model.checks, "marked elements.json")

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
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    return_code = app.exec()

    sys.exit(return_code)
