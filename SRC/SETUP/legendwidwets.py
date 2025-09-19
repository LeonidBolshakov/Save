from typing import Protocol
from PyQt6.QtWidgets import QCheckBox
from PyQt6 import QtCore


class HasLegendUi(Protocol):
    """
    Интерфейс (протокол) для объектов, содержащих виджеты легенды.

    Требуемые атрибуты:
        checkBox_no_select       : QCheckBox
        checkBox_partially_select: QCheckBox
        checkBox_select          : QCheckBox
        checkBox_auto_select     : QCheckBox
    """

    checkBox_partially_select: QCheckBox
    checkBox_select: QCheckBox


class Legend:
    """
    Управляет логикой легенды флажков.

    Принимает объект, удовлетворяющий протоколу HasLegendUi
    (например, экземпляр MainWindow после загрузки UI).
    """

    def __init__(self, ui: HasLegendUi) -> None:
        """
        Инициализирует ссылки на флажки легенды.

        Args:
            ui: объект, содержащий нужные QCheckBox,
                например self в MainWindow после uic.loadUi().
        """
        self.part = ui.checkBox_partially_select
        self.all = ui.checkBox_select

    def init_legend(self) -> None:
        """
        Выполняет базовую настройку легенды.

        Действия:
            • включает поддержку трёх состояний у частичного чекбокса;
            • здесь же подключается обработчик изменения флажков,
              который блокирует все изменения.
        """
        # Устанавливаем флажку неопределенное состояние
        self.part.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
        # Блокируем изменение флажков легенды
        self.part.stateChanged.connect(self._ignore_state_change)
        self.all.stateChanged.connect(self._ignore_state_change)

    def _ignore_state_change(self):
        self.part.setCheckState(QtCore.Qt.CheckState.PartiallyChecked)
        self.all.setCheckState(QtCore.Qt.CheckState.Checked)
