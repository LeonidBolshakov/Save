"""
Левая панель  — настройка задачи Windows Task Scheduler (GUI-обёртка).

Модуль связывает элементы пользовательского интерфейса (PyQt6) с логикой
работы планировщика задач Windows. Основные задачи:
- загрузка существующей WEEKLY-задачи (если она есть) и отражение её
  параметров в UI;
- создание/обновление задачи на основе заполненных полей;
- удаление задачи из планировщика;
- работа с переменными окружения и значениями «по умолчанию»;
- обработка COM-ошибок (HRESULT) и вывод человекочитаемых сообщений.

Структура:
- TaskConfig          — dataclass с параметрами задачи;
- TaskSchedulerService — тонкая обёртка над task_scheduler_win32;
- HasSchedulePanelUI  — протокол ожидаемых полей UI;
- ErrorFormater       — форматирование COM-ошибки в текст;
- SchedulePanel       — основной класс, управляющий левой панелью.
"""

from typing import Protocol, Any, Literal
from dataclasses import dataclass
from loguru import logger
import os
import pywintypes

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
    """
    Конфигурация задачи планировщика, собранная из UI.

    Атрибуты:
        task_path      : Полный путь к задаче в планировщике (\\Folder\\TaskName).
        mask_days      : 7-битная маска дней недели (bit0=Пн .. bit6=Вс).
        start_time     : Время запуска в формате "HH:MM".
        executable_path: Путь к исполняемому файлу.
        description    : Описание задачи (отображается в планировщике).
    """
    task_path                   : str
    mask_days                   : int
    start_time                  : str
    executable_path             : str
    description                 : str


class TaskSchedulerService:
    """Тонкая обёртка над task_scheduler для работы через TaskConfig.

    Позволяет SchedulePanel не зависеть напрямую от деталей реализации
    task_scheduler_win32 и облегчает модульное тестирование.
    """

    def create_or_replace(self, config: TaskConfig):
        """Создаёт или обновляет задачу по переданной конфигурации.

        Возвращает:
            None при успехе или pywintypes.com_error при COM-ошибке.
        """
        return task_scheduler.create_replace_task_scheduler(
            mask_days=config.mask_days,
            task_path=config.task_path,
            executable_path=config.executable_path,
            start_time=config.start_time,
            description=config.description,
        )

    def delete(self, task_path: str):
        """Удаляет задачу по пути task_path, возвращая None или com_error."""
        return task_scheduler.delete_task_scheduler(task_path)

class HasSchedulePanelUI(Protocol):
    """
    Протокол минимального набора атрибутов UI, необходимых SchedulePanel.

    Используется для статической проверки типов: любой объект, реализующий
    эти атрибуты, может быть передан в SchedulePanel.
    """
    label_task_location         : QLabel
    textEdit_program_path       : QPlainTextEdit
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
    """
    Форматирование COM-ошибок в человекочитаемый текст.

    Использует карту HRESULT → описания и функцию extract_hresult из
    task_scheduler_win32 для корректного извлечения кода ошибки.
    """

    def __init__(self, hresult_map: dict[int, str]) -> None:
        self._map = hresult_map

    def format_com_error(self, error: pywintypes.com_error) -> str:  # type: ignore[attr-defined]
        """
        Анализирует объект pywintypes.com_error и возвращает человекочитаемое сообщение.

        Поведение:
            - корректно извлекает настоящий HRESULT (внешний или внутренний);
            - при наличии описания в карте _HRESULT_MAP возвращает его;
            - иначе формирует общее сообщение с указанием кода ошибки.

        Args:
            error: Исключение COM.

        Returns:
            Строка с описанием ошибки для вывода пользователю.
        """
        hr = task_scheduler.extract_hresult(error)

        return self._map.get(
            hr, f"Ошибка COM (HRESULT=0x{hr:08X}). См. лог для деталей."
        )


class SchedulePanel:
    """
    Панель управления настройками задачи планировщика.

    Этот класс «склеивает»:
      - PyQt-виджеты левой панели;
      - переменные окружения (значения по умолчанию);
      - низкоуровневую работу с Windows Task Scheduler.

    Основные сценарии:
      * при инициализации — попытка прочитать существующую задачу, при неудаче ввести параметры задачи по умолчанию;
      * пользователь меняет описание, время и дни недели и создаёт/обновляет задачу;
      * пользователь удаляет задачу;
      * при ошибках COM пользователь получает понятное сообщение.
    """

    def __init__(self, ui: HasSchedulePanelUI) -> None:
        """
        Инициализирует панель работы с задачей планировщика.

        Args:
            ui: Объект с необходимыми виджетами (см. HasSchedulePanelUI).

        В процессе инициализации:
          - привязывает виджеты к полям класса;
          - настраивает стили кнопок;
          - читает задачу из планировщика (если есть);
          - подключает сигналы кнопок и полей ввода.
        """
        self._bind_ui(ui)
        init_button_styles(self)

        # Сохраняем исходное состояние кнопки создания задачи
        self._default_button_text = self.btn_create_task.text()
        self._default_button_slot = self.create_or_replace_task

        self._ui_default: bool = True  # UI сформировано из значений «по умолчанию»
        self._ui_dirty: bool = False  # пользователем были внесены изменения
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
        self.txt_program_path = ui.textEdit_program_path
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

        Алгоритм:
          1. Получаем папку и имя задачи из переменных окружения (C.TASK_FOLDER, C.TASK_NAME).
          2. Если они не заданы — блокируем левую панель и выводим сообщение.
          3. Пытаемся прочитать WEEKLY-задачу через task_scheduler.read_weekly_task().
          4. При успехе — отражаем параметры задачи в UI.
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
            # Некорректная структура задачи (например, не WEEKLY-триггер).
            msg = C.TEXT_TASK_MANUAL_EDIT.format(task=self.task_path)
            logger.error(msg)
            self.put_to_info(msg)
            self._lock_left_panel_widgets(enable=False)
            self._set_task_button_mode("delete")

        # Если задача не считана или недостоверная задача, предлагаем создать или удалить задачу
        self.set_button_create_active(self.btn_create_task, True)

    def _btn_signal_connect(self) -> None:
        """Подключает сигналы кнопок и полей ввода к слотам SchedulePanel."""
        self.btn_select_all_day.clicked.connect(self.on_select_all_day)
        self.btn_clean_all_day.clicked.connect(self.on_clean_all_day)
        self.btn_create_task.clicked.connect(self._default_button_slot)
        self.btn_reject_changes.clicked.connect(self.on_reject_all_changes)
        self.btn_delete_task.clicked.connect(self.on_delete_task_clicked)

        # Изменения текста / времени / чекбоксов → активировать кнопки «создать»/«отменить»
        self.txt_program_path.textChanged.connect(self.update_buttons_state_enable)
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
                self.txt_program_path, executable, from_env=False
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
        """
        Заполняет UI значениями по умолчанию (из constants / окружения).

        Используется, когда:
          - задача ещё не была создана;
          - задача была удалена;
        """

        self._ui_default = True
        self._ui_dirty = False

        self._apply_value_to_widget(self.txt_task_description, C.TASK_DESCRIPTION)
        self._apply_value_to_widget(self.txt_program_path, C.PROGRAM_PATH)
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
        Применяет значение к виджету.

        Если from_env=True — value трактуется как имя переменной окружения,
        в противном случае — как готовое значение.

        Возвращает:
            Значение, которое было фактически установлено или None при ошибке.
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

    def on_select_all_day(self) -> None:
        """Отмечает все дни недели (маска 1111111) и помечает UI как «изменённый»."""
        self._ui_dirty = True
        self.all_day(checked=True)

    def on_clean_all_day(self) -> None:
        """Снимает выделение со всех дней недели и помечает UI как «изменённый»."""
        self._ui_dirty = True
        self.all_day(checked=False)

    def create_or_replace_task(self) -> None:
        """
        Создаёт или обновляет WEEKLY-задачу в планировщике по текущим данным UI.

        Последовательность:
          1. Собирает TaskConfig (_get_current_task_config).
          2. Проверяет, что выбраны хотя бы один день недели.
          3. Вызывает TaskSchedulerService.create_or_replace().
          4. В случае ошибки — логирует подробности и выводит сообщение пользователю.
          5. В случае успеха — сбрасывает флаг «грязности» и отключает кнопки.
        """

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
            self.report_com_error(error, C.TASK_CREATED_ERROR)
            return

        # 5. Успешное сохранение — чистим состояние и UI
        self.finalize_task_save_ui()

    def on_reject_all_changes(self):
        """
        Откатывает все не сохранённые изменения.

        Если UI содержит значения по умолчанию — просто перезаполняет их,
        иначе — заново подгружает данные из считанной задачи.
        """
        if self._ui_default:
            self._update_ui_from_defaults()
        else:
            self._update_ui_from_task()

    def all_day(self, checked: bool) -> None:
        """
        Отмечает/снимает все чекбоксы дней недели в layout hbox_week_days.

        Args:
            checked: True — выделить все дни, False — снять выделение.
        """

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
            self.report_com_error(error, C.TASK_DELETED_ERROR)
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
        Используется при ошибках конфигурации задачи или при её удалении.
        """
        for child in self.group_box_left.findChildren(QWidget):
            if child is self.btn_create_task:
                continue
            child.setEnabled(enable)

    def _set_task_button_mode(self, mode: Literal["create", "delete"]) -> None:
        """
        Переключает кнопку между режимами создания и удаления задачи.

        Режимы:
            "create" — стандартный режим: кнопка создаёт/обновляет задачу;
            "delete" — альтернативный режим: кнопка удаляет некорректную задачу
                       и создаёт настройки по умолчанию.
        """

        try:
            self.btn_create_task.clicked.disconnect()
        except TypeError:
            # если ещё ничего не было подключено — избегаем ошибки
            pass

        if mode == "create":
            # Для кнопки восстанавливаем исходные текст и обработчик
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
        html_text = utils.make_html(message, color)
        self._apply_value_to_widget(self.text_info, html_text, from_env=False)

    def set_button_create_active(self, button: QPushButton, active: bool) -> None:
        """
        Делает кнопку «создать» активной/пассивной с точки зрения фокуса и default-состояния.

        active=True:
            - кнопка становится default и получает фокус;
        active=False:
            - фокус возвращается на group_box_left (панель).
        """

        if active:
            button.setDefault(True)
            button.setFocus()
        else:
            if self.group_box_left is not None:
                self.group_box_left.setFocus()

    def update_buttons_state_enable(self):
        """
        Помечает UI как «изменённый» и включает кнопки «создать» и «отменить изменения».

        Вызывается при любых изменениях в текстовых полях, времени или чекбоксах.
        """

        self._ui_dirty = True
        self.update_buttons_state(enabled=True)

    def update_buttons_state(self, *, enabled: bool) -> None:
        """Включает/выключает кнопки 'Создать задачу' и 'Отказаться от изменен.'."""
        self.btn_create_task.setEnabled(enabled)
        self.btn_reject_changes.setEnabled(enabled)

    def confirm_delete_task(self) -> bool:
        """
        Показывает диалог подтверждения удаления задачи.

        Returns:
            True, если пользователь подтвердил удаление, иначе False.
        """

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
        """Возвращает окно-владелец для диалоговых окон сообщений."""
        return self.group_box_left.window()

    def _get_current_task_config(self) -> TaskConfig:
        """
        Собирает текущие значения из UI и возвращает TaskConfig.

        Внутренний вспомогательный метод: сюда стягивается вся логика
        извлечения параметров из виджетов.
        """

        return TaskConfig(
            task_path=self.task_path,
            mask_days=self.get_week_mask(),
            executable_path=self.txt_program_path.toPlainText(),
            start_time=self.time_task_start.time().toString("HH:mm"),
            description=self.txt_task_description.toPlainText(),
        )

    def report_com_error(self, error, user_message_prefix: str) -> None:
        """
        Логирует подробную COM-ошибку и выводит человекочитаемое сообщение в UI.

        Args:
            error: pywintypes.com_error
            user_message_prefix: текст, который выводится перед сообщением
                                 (например: C.TASK_CREATED_ERROR).
        """
        hr, msg, details = task_scheduler.extract_com_error_info(error)

        logger.exception(
            "%s HRESULT=0x%08X, message=%s, details=%s",
            user_message_prefix.strip(),
            hr,
            msg,
            details,
        )

        readable = self.error_formatter.format_com_error(error)
        self.put_to_info(f"{user_message_prefix}\n{readable}")

    def finalize_task_save_ui(self) -> None:
        """
        Приводит интерфейс в состояние после успешного создания/обновления задачи.
        Сбрасывает флаги изменений, выводит сообщение, включает/отключает нужные кнопки.
        """
        self.set_button_create_active(self.btn_create_task, active=False)
        self._ui_dirty = False
        self.update_buttons_state(enabled=False)
        self.put_to_info(C.TASK_CREATED_SUCSESSFULL, color="green")
        logger.info(C.TASK_CREATED_SUCSESSFULL)
        self.btn_delete_task.setEnabled(True)
