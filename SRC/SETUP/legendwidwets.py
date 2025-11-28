"""
Модуль legend
=============

Содержит вспомогательный тип и класс для инициализации легенды чекбоксов —
элементов интерфейса, которые должны отображать фиксированное состояние
(Checked / PartiallyChecked), но не должны изменяться пользователем.

Почему это делается кодом
-------------------------

Qt Designer НЕ умеет создавать QCheckBox, который:
    отображает состояние (checked / partiallyChecked)
    и НЕ позволяет пользователю его изменить.

Проблемы возможных подходов в Designer:
    • setCheckable(False) — галка не отображается;
    • setEnabled(False) — виджет становится серым, что некорректно для легенды.

Правильный способ — установить состояние программно и
заблокировать любые события от пользователя:

    • WA_TransparentForMouseEvents — игнорирование кликов мыши;
    • NoFocus — невозможность получить фокус клавиатурой.

Протокол HasLegendUi включает только два чекбокса:
    • частично выбран
    • выбран

Именно эти элементы должны быть фиксированными. Остальная часть легенды
формируется QtDesigner.
"""

from typing import Protocol

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox


class HasLegendUi(Protocol):
    """
    Интерфейс для объектов, содержащих чекбоксы легенды.

    Атрибуты:
        checkBox_partially_select : QCheckBox
            Состояние "частично выбран".
        checkBox_select           : QCheckBox
            Состояние "выбран".

    Примечание:
        Легенда использует только эти два чекбокса, так как они должны
        находиться в фиксированном состоянии. Остальные элементы легенды
        (если есть) не нуждаются в программной обработке.
    """

    checkBox_partially_select: QCheckBox
    checkBox_select: QCheckBox


class Legend:
    """
    Управляет логикой чекбоксов легенды: задаёт им состояния и блокирует
    возможность их изменения пользователем.

    Использование:

        legend = Legend(self.ui)
        legend.init_legend()
    """

    def __init__(self, ui: HasLegendUi) -> None:
        """
        Сохраняет ссылки на чекбоксы легенды.

        Args:
            ui : объект, содержащий требуемые чекбоксы:
                 checkBox_partially_select и checkBox_select.
        """
        self.partially = ui.checkBox_partially_select
        self.selected = ui.checkBox_select

    def init_legend(self) -> None:
        """
        Настраивает чекбоксы легенды:

            • включает tristate у частично выбранного;
            • задаёт нужные состояния;
            • блокирует взаимодействие пользователя с чекбоксами.
        """
        # Чекбокс "частично выбран"
        self.partially.setTristate(True)
        self.partially.setCheckState(Qt.CheckState.PartiallyChecked)
        self._make_readonly(self.partially)

        # Чекбокс "выбран"
        self.selected.setCheckState(Qt.CheckState.Checked)
        self._make_readonly(self.selected)

    @staticmethod
    def _make_readonly(widget: QCheckBox) -> None:
        """
        Делает чекбокс полностью «только для отображения».

        Виджет остаётся визуально включённым и сохраняет состояние,
        но НЕ реагирует на мышь и клавиатуру.
        """
        widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
