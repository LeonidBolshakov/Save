from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import QLineEdit, QToolButton, QFileDialog


class PathSelector(QObject):
    """
    Контроллер выбора пути для связки `QLineEdit` + `QToolButton`.

    Класс **не является виджетом** и не участвует в layout’ах.
    Он инкапсулирует логику выбора и отображения пути, работая
    поверх уже существующих элементов интерфейса.

    Основные обязанности:
    - хранить полный путь (`_full_path`);
    - отображать укороченную (elided) версию пути в `QLineEdit`;
    - показывать полный путь в tooltip;
    - реагировать на изменение размера `QLineEdit`;
    - эмитить сигнал `path_changed` при смене пути.

    Сигналы
    -------
    path_changed(str)
        Испускается при изменении полного пути.
    """

    path_changed = pyqtSignal(str)

    def __init__(
        self,
        path_edit: QLineEdit,
        choose_btn: QToolButton,
        parent: QObject | None = None,
    ) -> None:
        """
        Создать контроллер выбора пути.

        Parameters
        ----------
        path_edit : QLineEdit
            Поле для отображения пути.
            Обычно используется в режиме `readOnly`.
        choose_btn : QToolButton
            Кнопка открытия диалога выбора пути.
        parent : QObject | None, optional
            Родительский объект Qt (по умолчанию None).
        """
        super().__init__(parent)

        self.path_edit = path_edit
        self.choose_btn = choose_btn
        self._full_path: str | None = None

        self.choose_btn.clicked.connect(self.on_choose_clicked)

        # Отслеживаем реальные изменения размера QLineEdit
        self.path_edit.installEventFilter(self)

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def set_path(self, path: str) -> None:
        """
        Установить новый путь, можно извне.

        Если путь не изменился, метод ничего не делает.

        Parameters
        ----------
        path : str
            Полный путь к файлу или каталогу.
        """
        if path is None:
            return

        path = str(path)
        if path == self._full_path:
            return

        self._full_path = path
        self._update_displayed_path()
        self.path_edit.setToolTip(self._full_path)
        # noinspection PyUnresolvedReferences
        self.path_changed.emit(self._full_path)
        return

    def get_path(self) -> str:
        """
        Получить текущий полный путь.

        Returns
        -------
        str
            Полный путь, сохранённый в контроллере.
        """
        return self._full_path

    # ------------------------------------------------------------------
    # Логика выбора пути (переопределяется в наследниках)
    # ------------------------------------------------------------------

    def choose_path(self) -> str:
        """
        Открыть диалог выбора пути.

        Метод **обязан быть переопределён** в наследниках.

        Returns
        -------
        str
            Выбранный путь или пустая строка, если выбор отменён.
        """
        raise NotImplementedError

    def on_choose_clicked(self) -> None:
        """
        Обработчик нажатия кнопки выбора пути.
        """
        new_path = self.choose_path()
        if new_path is not None:
            self.set_path(new_path)

    # ------------------------------------------------------------------
    # Отображение пути с усечением
    # ------------------------------------------------------------------

    def _update_displayed_path(self) -> None:
        """
        Обновить отображаемый текст в `QLineEdit`.

        Текст усекётся посередине (`ElideMiddle`) в зависимости
        от текущей доступной ширины поля ввода.
        """
        if not self._full_path:
            self.path_edit.setText("")
            return

        fm = QFontMetrics(self.path_edit.font())
        available_width = self.path_edit.contentsRect().width()

        if available_width <= 0:
            # Виджет ещё не разложен layout’ом
            self.path_edit.setText(self._full_path)
            return

        elided = fm.elidedText(
            self._full_path,
            Qt.TextElideMode.ElideMiddle,
            available_width,
        )
        self.path_edit.setText(elided)

    # ------------------------------------------------------------------
    # Отслеживание событий
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        """
        Перехват событий Qt.

        Используется для отслеживания изменения размера `QLineEdit`
        и пересчёта укороченного текста.
        """
        if obj is self.path_edit and event.type() == QEvent.Type.Resize:
            self._update_displayed_path()
        return False


class ProgramSelector(PathSelector):
    """
    Контроллер выбора исполняемого файла программы.
    """

    def choose_path(self) -> str:
        """
        Открыть диалог выбора исполняемого файла.

        Returns
        -------
        str
            Путь к выбранному файлу или пустая строка.
        """
        file_name, _ = QFileDialog.getOpenFileName(
            None,
            "Выберите программу",
            "",
            "Исполняемые файлы (*.exe *.com *.bat);;Все файлы (*)",
        )
        return file_name or None


class WorkDirSelector(PathSelector):
    """
    Контроллер выбора рабочей директории.
    """

    def choose_path(self) -> str:
        """
        Открыть диалог выбора каталога.

        Returns
        -------
        str
            Путь к выбранной директории или пустая строка.
        """
        dir_name = QFileDialog.getExistingDirectory(
            None,
            "Выберите рабочую папку",
            "",
        )
        return dir_name or None
