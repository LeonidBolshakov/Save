from __future__ import annotations

from typing import Protocol, Any, Literal
from dataclasses import dataclass
import pywintypes
import logging
import html
import os

from PyQt6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QTimeEdit,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QLayout,
)
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
import SRC.SETUP.utils as utils
import SRC.SETUP.task_scheduler_win32 as task_scheduler
from SRC.SETUP.initbuttonstyle import init_button_styles

logger = logging.getLogger(__name__)

_HRESULT_MAP = {
    # Общие COM-ошибки
    0x80070005: "Отказано в доступе. Запустите программу с достаточными правами.",
    0x800706BA: "Служба RPC недоступна. Проверьте, запущена ли служба 'Task Scheduler' и RPC.",
    0x80040154: "COM-класс не зарегистрирован. Возможна проблема с системными компонентами.",
    0x800401F0: "COM не инициализирован. Требуется вызов CoInitialize/CoInitializeEx.",
    # Специфичные для планировщика задач
    0x80041309: "Ошибка триггера задачи (SCHED_E_TRIGGER_NOT_FOUND). Проверьте параметры триггера.",
    0x8004130F: "Некорректное описание задачи (SCHED_E_INVALID_TASK). Проверьте XML/параметры задачи.",
    0x8004131F: "Задача не готова к запуску (SCHED_E_TASK_NOT_READY). Условия/триггеры не удовлетворены.",
    0x80041318: "Задача не запущена (SCHED_E_TASK_NOT_RUNNING).",
    0x8004131E: "Не указано время начала задачи (SCHED_E_MISSING_START_TIME).",
}


# fmt: off
@dataclass
class TaskConfig:
    task_path                   : str
    mask_days                   : int
    start_time                  : str
    executable_path             : str
    description                 : str


class TaskSchedulerService:
    """Тонкая обёртка над task_scheduler для работы через TaskConfig."""

    def create_or_replace(self, config: TaskConfig):
        return task_scheduler.create_replace_task_scheduler(
            mask_days=config.mask_days,
            task_path=config.task_path,
            executable_path=config.executable_path,
            start_time=config.start_time,
            description=config.description,
        )

    def delete(self, task_path: str):
        return task_scheduler.delete_task_scheduler(task_path)

class HasSchedulePanelUI(Protocol):
    label_task_location         : QLabel
    label_program_path          : QLabel
    label_task_name             : QLabel
    textEdit_task_description   : QPlainTextEdit
    timeEdit_task_start_in      : QTimeEdit
    btn_clean_all_day           : QPushButton
    btn_reject_changes          : QPushButton
    btn_select_all_day          : QPushButton
    btn_create_task             : QPushButton
    btn_delete_task             : QPushButton
    hbox_week_days              : QHBoxLayout
    textEdit_Error              : QTextEdit
    groupBoxLeft                : QGroupBox
# fmt: on


class ErrorFormater:
    def __init__(self, hresult_map: dict[int, str]) -> None:
        self._map = hresult_map

    def format_com_error(self, error: pywintypes.com_error) -> str:  # type: ignore[attr-defined]
        """
        Анализирует объект pywintypes.com_error и возвращает человекочитаемое сообщение.

        - Корректно извлекает настоящий HRESULT (внешний или внутренний).
        - Использует карту _HRESULT_MAP.
        - Возвращает описание или сообщение по умолчанию.
        """
        hr = task_scheduler.extract_hresult(error)

        return self._map.get(
            hr, f"Ошибка COM (HRESULT=0x{hr:08X}). См. лог для деталей."
        )


class SchedulePanel:
    def __init__(self, ui: HasSchedulePanelUI) -> None:
        """
        Инициализирует панель работы с задачей планировщика.
        """
        self._bind_ui(ui)
        init_button_styles(self)

        # Сохраняем исходное состояние кнопки создания задачи
        self._default_button_text = self.btn_create_task.text()
        self._default_button_slot = self.create_or_replace_task

        self._ui_default: bool = True
        self._ui_dirty: bool = False
        self.error_formatter = ErrorFormater(_HRESULT_MAP)
        self.scheduler = TaskSchedulerService()
        self.env = EnvironmentVariables()
        self._init_ui_from_task()
        self._btn_signal_connect()

    def _bind_ui(self, ui: HasSchedulePanelUI) -> None:
        """
        Связывает элементы пользовательского интерфейса (UI) с атрибутами класса.
        """
        self.lbl_task_folder = ui.label_task_location
        self.lbl_program_path = ui.label_program_path
        self.lbl_task_name = ui.label_task_name
        self.txt_task_description = ui.textEdit_task_description
        self.time_task_start = ui.timeEdit_task_start_in
        self.btn_select_all_day = ui.btn_select_all_day
        self.btn_create_task = ui.btn_create_task
        self.btn_delete_task = ui.btn_delete_task
        self.btn_clean_all_day = ui.btn_clean_all_day
        self.btn_reject_changes = ui.btn_reject_changes
        self.text_info = ui.textEdit_Error
        self.group_box_left = ui.groupBoxLeft

        # Чекбоксы дней недели (Пн-Вс) внутри hbox_week_days
        self.hbox_week_days = ui.hbox_week_days

    def _init_ui_from_task(self) -> None:
        """
        Загружает задачу планировщика (если есть) и обновляет UI.
        Если задача отсутствует или недоступна — загружает значения по умолчанию.
        """
        # Папка и имя задачи — сначала выводим в UI из переменных окружения
        task_folder = self._apply_value_to_widget(self.lbl_task_folder, C.TASK_FOLDER)
        task_name = self._apply_value_to_widget(self.lbl_task_name, C.TASK_NAME)

        if not task_folder or not task_name:
            msg = C.TEXT_NOT_TASK
            logger.error(msg)
            self._lock_left_panel_widgets(enable=False)
            self.btn_create_task.setEnabled(False)
            self.put_to_info(msg)
            return

        # Собираем путь к задаче
        self.task_path = os.path.join(task_folder, task_name)

        try:
            self.task_info = task_scheduler.read_weekly_task(self.task_path)
            self._update_ui_from_task()
            return
        except pywintypes.com_error:  # type: ignore[attr-defined]
            logger.warning(f"Задача {self.task_path} не найдена или недоступна")
            self._update_ui_from_defaults()
        except ValueError:
            msg = C.TEXT_TASK_MANUAL_EDIT.format(task=self.task_path)
            logger.error(msg)
            self.put_to_info(msg)
            self._lock_left_panel_widgets(enable=False)
            self._set_task_button_mode("delete")
        self.set_button_create_active(self.btn_create_task, True)

    def _btn_signal_connect(self) -> None:
        self.btn_select_all_day.clicked.connect(self.select_all_day)
        self.btn_clean_all_day.clicked.connect(self.clean_all_day)
        self.btn_create_task.clicked.connect(self._default_button_slot)
        self.btn_reject_changes.clicked.connect(self.reject_all_changes)
        self.btn_delete_task.clicked.connect(self.on_delete_task_clicked)

        self.txt_task_description.textChanged.connect(self.update_buttons_state_enable)
        self.time_task_start.timeChanged.connect(self.update_buttons_state_enable)
        utils.connect_checkboxes_in_layout(
            self.hbox_week_days, self.update_buttons_state_enable
        )

    def _update_ui_from_task(self) -> None:
        """
        Обновляет UI на основе данных задачи, полученных из read_weekly_task().
        Ожидаются ключи:
          - mask_days
          - start_time
          - executable
          - description
        """
        self._ui_default = False
        # Описание задачи
        description = self.task_info.get("description")
        if description is not None:
            self._apply_value_to_widget(
                self.txt_task_description, description, from_env=False
            )

        # Путь к программе
        executable = self.task_info.get("executable")
        if executable is not None:
            self._apply_value_to_widget(
                self.lbl_program_path, executable, from_env=False
            )

        # Маска дней недели
        self._set_week_mask(self.task_info.get("mask_days"))

        # Время запуска
        start_time = self.task_info.get("start_time")
        if start_time is not None:
            self._apply_value_to_widget(
                self.time_task_start, start_time, from_env=False
            )

        self._ui_dirty = False
        self.update_buttons_state(enabled=False)

    def _update_ui_from_defaults(self) -> None:
        self._ui_default = True
        self._ui_dirty = False

        self._apply_value_to_widget(self.txt_task_description, C.TASK_DESCRIPTION)
        self._apply_value_to_widget(self.lbl_program_path, C.PROGRAM_PATH)
        self._apply_value_to_widget(self.hbox_week_days, C.SCHEDULED_DAYS_MASK)
        self._apply_value_to_widget(self.time_task_start, C.TASK_START_IN)
        self.put_to_info(C.TASK_NOT_CREATED)

    def _apply_value_to_widget(
            self,
            widget: QWidget | QLayout,
            value: str,
            *,
            from_env: bool = True,
    ) -> Any | None:
        """
        Применяет значение к виджету и возвращает его.
        Если from_env=True — var_name трактуется как имя переменной окружения.
        """
        if from_env:
            env_value = self.env.get_var(value)
            if env_value is None:
                logger.error(f"Переменная {value} не задана в окружении.")
                return None
        else:
            # var_name уже является самим значением, а не именем переменной
            env_value = value

        return_text = utils.set_widget_value(widget, env_value, empty=C.TEXT_EMPTY)
        if return_text:
            logger.error(
                f"Ошибка при установке значения для {env_value}\n{return_text}"
            )
            return None

        return env_value

    @staticmethod
    def make_html(text: str, color: str) -> str:
        """
        Формирует небольшой HTML-фрагмент для вывода в QTextEdit:
        - color управляет цветом текста
        - font-weight подбирается автоматически по цвету
        """
        # Экранируем спецсимволы и переводим \n в <br>
        safe_text = html.escape(text).replace("\n", "<br>")

        # Подбираем цвет и насыщенность шрифта
        if color == "green":  # успех
            css_color = "#2e7d32"
            font_weight = "500"
        elif color == "red":  # ошибка
            css_color = "#c62828"
            font_weight = "600"
        else:  # информационные сообщения
            css_color = color  # можно "black" или другой цвет
            font_weight = "400"

        return (
            f"{utils.HTML_TEG}"
            f'<div style="text-align:center;">'
            f'<span style="color:{css_color}; font-weight:{font_weight};">'
            f"{safe_text}"
            f"</span>"
            f"</div>"
        )

    def select_all_day(self) -> None:
        self._ui_dirty = True
        self.all_day(checked=True)

    def clean_all_day(self) -> None:
        self._ui_dirty = True
        self.all_day(checked=False)

    def create_or_replace_task(self) -> None:

        # 1. Собираем конфигурацию задачи из UI
        config = self._get_current_task_config()

        # 2. Проверяем, выбраны ли дни
        if config.mask_days == 0:
            self.put_to_info(C.TEXT_NO_DAY)
            return

        # 3. Вызываем сервис
        error = self.scheduler.create_or_replace(config)

        # 4. Обрабатываем результат
        if error:
            hr, msg, details = task_scheduler.extract_com_error_info(error)

            logger.exception(
                "Ошибка при создании задачи в планировщике. "
                "HRESULT=0x%08X, message=%s, details=%s",
                hr,
                msg,
                details,
            )

            message = self.error_formatter.format_com_error(error)
            self.put_to_info(C.TASK_CREATED_ERROR + "\n" + message)
            return

        # 5. Успешное сохранение — чистим состояние и UI
        self.set_button_create_active(self.btn_create_task, active=False)
        self._ui_dirty = False
        self.update_buttons_state(enabled=False)
        self.put_to_info(C.TASK_CREATED_SUCSESSFULL, color="green")
        logger.info(C.TASK_CREATED_SUCSESSFULL)
        self.btn_delete_task.setEnabled(True)

    def reject_all_changes(self):
        if self._ui_default:
            self._update_ui_from_defaults()
        else:
            self._update_ui_from_task()

    def all_day(self, checked: bool) -> None:
        for i in range(self.hbox_week_days.count()):
            item = self.hbox_week_days.itemAt(i)
            w = item.widget() if item is not None else None
            if isinstance(w, QCheckBox):
                w.setChecked(checked)

    def get_week_mask(self) -> int:
        """
        Строит битовую маску дней недели по состоянию чекбоксов.
        bit0 = первый чекбокс (Пн), ..., bit6 = последний (Вс).
        """
        mask = 0
        for i in range(self.hbox_week_days.count()):
            item = self.hbox_week_days.itemAt(i)
            w = item.widget() if item is not None else None
            if isinstance(w, QCheckBox) and w.isChecked():
                mask |= 1 << i
        return mask

    def _set_week_mask(self, mask: int | None) -> None:
        """
        Устанавливает состояния чекбоксов дней недели согласно битовой маске.
        bit0 = первый чекбокс (обычно Пн), ..., bit6 = последний (обычно Вс).

        Если mask is None — просто снимаем все галочки.
        """
        if mask is None:
            self.all_day(False)
            return

        for i in range(self.hbox_week_days.count()):
            item = self.hbox_week_days.itemAt(i)
            w = item.widget() if item is not None else None
            if isinstance(w, QCheckBox):
                w.setChecked(bool(mask & (1 << i)))

    def on_delete_task_clicked(self) -> None:
        """Слот для кнопки 'Удалить задачу'."""
        # Флаг "грязности" здесь лучше не трогать, он обнуляется
        # внутри _update_ui_from_defaults после успешного удаления.
        if not self.confirm_delete_task():
            return

        if self.delete_task():
            self.put_to_info(C.TASK_DELETED_SUCSESSFULL, color="green")
            logger.info(C.TASK_DELETED_SUCSESSFULL)
            self.btn_delete_task.setEnabled(False)

    def delete_task(self) -> bool:
        """
        Удаляет задачу через сервис планировщика и,
        при успехе, приводит UI к состоянию 'задачи нет'.
        """
        error = self.scheduler.delete(self.task_path)
        if error is not None:
            hr, msg, details = task_scheduler.extract_com_error_info(error)

            logger.exception(
                "Ошибка при удалении задачи в планировщике. "
                "HRESULT=0x%08X, message=%s, details=%s",
                hr,
                msg,
                details,
            )

            message = self.error_formatter.format_com_error(error)
            self.put_to_info(C.TASK_DELETED_ERROR + "\n" + message)
            return False

        # Успешное удаление: разблокируем левую панель,
        # возвращаем режим "создания", сбрасываем UI в значения по умолчанию
        self._lock_left_panel_widgets(enable=True)
        self._set_task_button_mode("create")
        self._update_ui_from_defaults()
        self._ui_dirty = False
        return True

    def _lock_left_panel_widgets(self, enable: bool) -> None:
        """
        Включает / отключает все виджеты в левой панели, кроме кнопки создания задачи.
        """
        for child in self.group_box_left.findChildren(QWidget):
            if child is self.btn_create_task:
                continue
            child.setEnabled(enable)

    def _set_task_button_mode(self, mode: Literal["create", "delete"]) -> None:
        """Переключает кнопку между режимами создания и удаления задачи."""
        try:
            self.btn_create_task.clicked.disconnect()
        except TypeError:
            # если ещё ничего не было подключено — избегаем ошибки
            pass

        if mode == "create":
            # Для кнопки восстанавливаем исходный текст и обработчик
            self.btn_create_task.setText(self._default_button_text)
            self.btn_create_task.clicked.connect(self._default_button_slot)
        elif mode == "delete":
            self.btn_create_task.setText(
                "Удалить задачу\nСоздать настройки\nпо умолчанию"
            )
            self.btn_create_task.clicked.connect(self.delete_task)
        else:
            msg = f"Функция _set_task_button_mode. Неверно задан параметр mode - {mode}"
            logger.error(msg)
            raise ValueError(msg)

    def put_to_info(self, message: str, color: str = "red") -> None:
        """
        Выводит сообщение в поле text_info с нужным цветом и насыщенностью шрифта.
        Цвет влияет и на font-weight (успех/ошибка/инфо).
        """
        html_text = self.make_html(message, color)
        self._apply_value_to_widget(self.text_info, html_text, from_env=False)

    def set_button_create_active(self, button: QPushButton, active: bool) -> None:
        if active:
            button.setDefault(True)
            button.setFocus()
        else:
            if self.group_box_left is not None:
                self.group_box_left.setFocus()

    def update_buttons_state_enable(self):
        self._ui_dirty = True
        self.update_buttons_state(enabled=True)

    def update_buttons_state(self, *, enabled: bool) -> None:
        self.btn_create_task.setEnabled(enabled)
        self.btn_reject_changes.setEnabled(enabled)

    def confirm_delete_task(self) -> bool:
        msg = QMessageBox(self._msg_parent())
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Подтверждение удаления")
        msg.setText("Удалить задачу?")
        msg.setInformativeText("После удаления задача будет безвозвратно удалена.")

        # Кнопки
        delete_btn = msg.addButton("Удалить", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)

        # По умолчанию фокус — на Отмена
        msg.setDefaultButton(cancel_btn)

        msg.exec()

        return msg.clickedButton() is delete_btn

    def _msg_parent(self) -> QWidget | None:
        return self.group_box_left.window()

    def _get_current_task_config(self) -> TaskConfig:
        return TaskConfig(
            task_path=self.task_path,
            mask_days=self.get_week_mask(),
            executable_path=self.lbl_program_path.text(),
            start_time=self.time_task_start.time().toString("HH:mm"),
            description=self.txt_task_description.toPlainText(),
        )
