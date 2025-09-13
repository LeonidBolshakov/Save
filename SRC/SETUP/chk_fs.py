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


# ----- 1. УТИЛИТЫ: сохранить/загрузить МНОЖЕСТВО путей как JSON-список и вспомогательные функции.


def save_set_json(items: set[str], path: str | Path = "marked elements.json") -> None:
    """
    Сохранить множество строк в JSON-файл.
    Сортировка даёт детерминированный порядок строк в файле.

    :param items: Множество полных путей отмеченных элементов(папок/файлов)
    :param path: Путь фала для сохранения данных.
    :return:    None
    """
    p = Path(path)

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        error_handling(3, p, e)
    except OSError as e:
        error_handling(4, p, e)

    try:
        # ensure_ascii=False — кириллица пишется «как есть» в UTF‑8.
        with p.open("w", encoding="utf-8") as f:
            json.dump(sorted(items), f, ensure_ascii=False, indent=2)
    except PermissionError as e:
        error_handling(3, p, e)
    except OSError as e:
        error_handling(4, p, e)


def get_set_marked_files(p: Path) -> set[str]:
    """
    Возвращает множество ранее помеченных файлов/папок

    :param p: Путь на файл
    :return: Множество с ранее помеченными файлами/папками
    """
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return {str(x) for x in data}


def error_handling(error_number: int, p: Path, e: Exception | None = None) -> set[str]:
    """
    Обработка ошибок (печать)

    :param error_number:    Номер ошибки. Текст ошибки берётся из кортежа ERROR_TEXT.
                            Номер ошибки - номер элемента в кортеже.
    :param p: Путь к файлу источнику ошибки.
    :param e: Прерывание, которе вызвала ошибка
    :return: Пустое множество.
    """
    ERROR_TEXT = (
        f"Файла с пометками сохраняемых файлов/каталогов {p} не обнаружен.\n"  # 0
        f"Начинаем работу 'с чистого листа'",
        f"Нарушена структура файла с пометками сохраняемых файлов/каталогов {p}\n"  # 1
        f"{e}\n"
        f"Считаем что такого файла нет",
        f"Нет доступа к файлу с пометками сохраняемых файлов/каталогов {p}\n"  # 2
        f"{e}\n"
        f"Считаем что такого файла нет",
        f"Не могу сохранить информацию об отмеченных файлах/каталогах. Нет доступа к файлу {p}\n"  # 3
        f"{e}\n",
        f"Не могу сохранить информацию об отмеченных файлах/каталогах. Ошибка вывода {p}\n"  # 4
        f"{e}\n",
    )
    print(ERROR_TEXT[error_number])
    return set()


def load_set_json(path: str | Path = "marked elements.json") -> set[str]:
    """Загрузить множество строк из JSON-списка. Отсутствующий файл → пустое множество.
    Ошибки парсинга гасим и возвращаем пустое множество, чтобы не падать при старте.
    """
    p = Path(path)

    try:
        return get_set_marked_files(p)
    except FileNotFoundError:
        return error_handling(0, p)
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as e:
        return error_handling(1, p, e)
    except PermissionError as e:
        return error_handling(2, p, e)


# ----- 2. ПРОКСИ-МОДЕЛЬ: визуализация Checked / PartiallyChecked без изменения self.checks


class CheckableFSModel(QIdentityProxyModel):
    """Прокси над QFileSystemModel с checkboxes в колонке 0

    * self.checks: set[str] — набор ПОЛНЫХ путей, которые пользователь явно отметил.
    Визуально:
      - Если путь в self.checks → Checked.
      - Если путь в self.checks является директорией, то все нижестоящие элементы помечаются "серыми" Checked
      - Если путь — директория и в self.checks есть её потомки → PartiallyChecked.
      - Иначе → Unchecked.
    При этом «серые» галки считаются вычислёнными и в self.checks НЕ пишутся.
    """

    # Инициализация модели

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Загружаем отмеченные пути файлов/директорий из файла и нормализуем до единого вида
        self.checks: set[str] = self.get_checks()

    def get_checks(self) -> set[str]:
        return {self._norm(p) for p in load_set_json()}

    # Рассылка обновлений: корректно и адресно

    def _emit_branch_changed(self, index: QModelIndex) -> None:
        """
        Поднимаемся по ветке и для каждого родителя шлём dataChanged по всем детям.
        Это эффективный способ «пересчитать» PartiallyChecked на пути к корню.

        :param index: Индекс, от которого поднимаемся по дереву вверх
        :return: None
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
        """
        Рекурсивно посылает dataChanged для всех узлов поддерева.

        Используется для полного обновления CheckStateRole и ForegroundRole
        начиная с указанного родителя вниз по всем потомкам.

        :param parent: QModelIndex, корень поддерева для обновления
        :return: None
        """
        rows, cols = self.rowCount(parent), self.columnCount(parent)
        if rows > 0 and cols > 0:
            # Сигнал обновления для всех ячеек родителя
            tl = self.index(0, 0, parent)
            br = self.index(rows - 1, cols - 1, parent)
            self.dataChanged.emit(
                tl, br, [Qt.ItemDataRole.CheckStateRole, Qt.ItemDataRole.ForegroundRole]
            )
            # Рекурсивно обходим все строки и обновляем их поддеревья
            for r in range(rows):
                self._emit_subtree_changed(self.index(r, 0, parent))

    # Помощники для путей

    def _norm(self, p: str) -> str:
        """
        Нормализовать путь: убрать './..', привести разделители к '/'.
        Это упрощает сравнение путей как строк.

        :param p: Строковый путь
        :return: Нормализованный строковый путь
        """
        return QDir.cleanPath(p)

    def _is_dir(self, index: QModelIndex) -> bool:
        """
        Проверить, что индекс — директория в исходной QFileSystemModel.

        :param index: Индекс исходной модели
        :return: True, если элемент, соответствующий индексу, является директорией
        """
        src = self.mapToSource(index)
        model = self.sourceModel()
        return isinstance(model, QFileSystemModel) and model.isDir(src)

    def _path(self, index: QModelIndex) -> str:
        """
        Получить нормализованный абсолютный путь у индекса из исходной модели.
        :param index: Индекс исходной модели.
        :return: Нормализованный абсолютный путь.
        """
        src = self.mapToSource(index)
        model = self.sourceModel()
        if isinstance(model, QFileSystemModel):
            return self._norm(model.filePath(src))
        return ""

    # Проверка родства путей

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
        Нужна, если дети «наследуют» заливку/цвет и должны игнорировать клики.
        """
        # Поднимаемся по дереву и проверяем каждый путь в self.checks
        it = index.parent()
        while it.isValid():
            if self._path(it) in self.checks:
                return True
            it = it.parent()
        return False

    # data(): отдаём состояния чекбокса и цвета

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        """
        Возвращает данные для ячейки модели.

            • Для CheckStateRole в колонке 0 — состояние чекбокса с учётом
              явных отметок, предков и потомков.
            • Для ForegroundRole — цвет текста (тёмно-синий для явных отметок,
              серый при наследовании).
            • Для остальных ролей — базовая реализация.


        Реализация data() совместима с QIdentityProxyModel.data().
        Parameters
            ----------
            index : QModelIndex
                См. QIdentityProxyModel.data()
            role : int, optional
                См. QIdentityProxyModel.data()
        """
        # Обрабатываем только валидные индексы
        if not index.isValid():
            return super().data(index, role)

        # Делегат рисует checkbox только если на запрос с ролью CheckStateRole модель возвращает значение.
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            path = self._path(index)

            # 1. Явная отметка пользователя
            if path in self.checks:
                return Qt.CheckState.Checked

            # 2. у предков есть явная отметка → показываем галку, но это не «ручная»
            if self._has_checked_dir_ancestor(index):
                return Qt.CheckState.Checked

            # 3. частично: есть помеченные потомки
            if self._is_dir(index) and self._has_marked_descendant(path):
                return Qt.CheckState.PartiallyChecked

            # 4. По умолчанию нет галки
            return Qt.CheckState.Unchecked

        # Цветовое оформление
        if role == Qt.ItemDataRole.ForegroundRole:
            path = self._path(index)

            # явная отметка - тёмно-синий
            if path in self.checks:
                return QBrush(Qt.GlobalColor.darkBlue)

            # наследованная от родителя — серый
            if self._has_checked_dir_ancestor(index):
                return QBrush(Qt.GlobalColor.gray)

        # Остальное — базовая реализация
        return super().data(index, role)

    def flags(self, index) -> Qt.ItemFlag:
        """
        Возвращает флаги элемента модели.

        Если элемент наследует отметку от родителя, он становится
        недоступным и без чекбокса. Иначе разрешены выбор, изменение
        состояния чекбокса и активация элемента.

        Parameters
        ----------
        index : QModelIndex
            Индекс элемента, для которого запрашиваются флаги.

        Returns
        -------
        Qt. ItemFlag
            Набор флагов, описывающих доступность и поведение элемента.
        """
        fl = super().flags(index)
        if self._has_checked_dir_ancestor(index):
            # Если родитель уже помечен — запрещаем выбор и изменение чекбокса
            fl &= ~Qt.ItemFlag.ItemIsEnabled
            fl &= ~Qt.ItemFlag.ItemIsUserCheckable
        else:
            # Разрешаем выбор и работу с checkbox
            fl |= (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
        return fl

    # setData(): обработка клика по checkbox

    def setData(
        self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        # интересуют только checkbox колонки 0
        if (
            role != Qt.ItemDataRole.CheckStateRole
            or index.column() != 0
            or not index.isValid()
        ):
            return super().setData(index, value, role)

        # Запретить клик по «унаследованным» элементам
        if self._has_checked_dir_ancestor(index):
            return False

        # Вычисляем, что именно хотим записать в self.checks
        path = self._path(index)
        state = Qt.CheckState(value)

        if state == Qt.CheckState.Checked:
            # Checked → добавляем путь
            self.checks.add(path)
        else:
            # Unchecked → снимаем явную отметку
            self.checks.discard(path)

        # Обновляем ветку: родителя, самого индекса и соседей под тем же родителем
        self._emit_subtree_changed(index)  # вниз — чтобы дети перерисовались
        self._emit_branch_changed(index)  # вверх — чтобы родители пересчитали Partial
        return True


# ----- 3. ПРИМЕР closeEvent: сохранить набор перед закрытием окна (по месту вызова)


class MainWindow(QMainWindow):
    """
    Главное окно с QTreeView.
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

    def closeEvent(self, e) -> None:
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
