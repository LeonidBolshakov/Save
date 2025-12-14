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

from enum import Enum, auto
from typing import Protocol, Any, Literal, Callable
from dataclasses import dataclass

from loguru import logger
import pywintypes
from pathlib import Path

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
    QLineEdit,
    QToolButton,
)
from PyQt6.QtCore import QTime

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

HandlerType = Callable[[str], bool]

# Недопустимые символы в именах файлов и директорий Windows
INVALID_PATH_CHARACTERS = r'\/:*?"<>|'
# Windows запрещает зарезервированные имена устройств DOS
# (CON, PRN, AUX, NUL, COM1–COM9, LPT1–LPT9)
RESERVED_DOS_DEVICE_NAMES = frozenset(
    {
        ".",
        "..",
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)

# fmt: off
@dataclass
class TaskConfig:
    """
    Конфигурация задачи планировщика, собранная из UI.

    Атрибуты:
        task_path           : Полный путь к задаче в планировщике (\\Folder\\TaskName).
        mask_days           : 7-битная маска дней недели (bit0=Пн .. bit6=Вс).
        start_time          : Время запуска исполняемого файла в формате "HH:MM".
        executable_path     : Путь к исполняемому файлу.
        work_directory_path : Путь к рабочей директории
        description         : Описание задачи (отображается в планировщике).
    """
    task_path                   : str
    mask_days                   : int
    start_time                  : str
    executable_path             : str
    work_directory_path         : str
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
            work_directory_path=config.work_directory_path,
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
    label_task_location             : QLabel
    label_task_name                 : QLabel
    lineEdit_path_programm          : QLineEdit
    toolButton_path_programm        : QToolButton
    lineEdit_path_work_directory    : QLineEdit
    toolButton_work_directory       : QToolButton
    textEdit_task_description       : QPlainTextEdit
    timeEdit_task_start_in          : QTimeEdit
    btn_clean_all_day               : QPushButton
    btn_reject_changes              : QPushButton
    btn_select_all_day              : QPushButton
    btn_create_task                 : QPushButton
    btn_delete_task                 : QPushButton
    hbox_week_days                  : QHBoxLayout
    textEdit_Error                  : QTextEdit
    groupBoxLeft                    : QGroupBox
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


# fmt: off
class ControlType(Enum):
    TEXT            = auto()
    START_TIME      = auto()
    FILE_PATH       = auto()
    FOLDER_PATH     = auto()
    TASK_NAME       = auto()
    TASK_FOLDER     = auto()
    MASK_DAYS       = auto()


@dataclass
class DescrTaskFields:
    widget          : QWidget | QLayout
    name_env        : str
    control_type    : ControlType
    error_text      : str
    value_default   : str | None = None
# fmt: on


class SchedulePanel:
    """
    Панель управления настройками задачи планировщика.

    Этот класс «склеивает»:
      - PyQt-виджеты левой панели;
      - переменные окружения (значения по умолчанию);
      - низкоуровневую работу с Windows Task Scheduler.

    Основные сценарии:
      * при инициализации — попытка прочитать существующую задачу, при неудаче ввести параметры задачи по умолчанию;
      * пользователь может менять описание, время и дни недели и создавать/обновлять или удалять задачу;
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
        self._init_descr_task_fields()
        init_button_styles(self)

        # Кнопка создания задачи может менять своё назначение.
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
        self.parameter_error = False

    def _bind_ui(self, ui: HasSchedulePanelUI) -> None:
        """
        Связывает элементы пользовательского интерфейса (UI) с атрибутами класса.
        """
        self.lbl_task_folder = ui.label_task_location
        self.txt_program_path = ui.lineEdit_path_programm
        self.txt_work_directory_path = ui.lineEdit_path_work_directory
        self.lbl_task_name = ui.label_task_name
        self.txt_task_description = ui.textEdit_task_description
        self.start_time_task = ui.timeEdit_task_start_in
        self.btn_select_all_day = ui.btn_select_all_day
        self.btn_create_task = ui.btn_create_task
        self.btn_delete_task = ui.btn_delete_task
        self.btn_clean_all_day = ui.btn_clean_all_day
        self.btn_reject_changes = ui.btn_reject_changes
        self.btn_path_programm = ui.toolButton_path_programm
        self.btn_work_directory = ui.toolButton_work_directory
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

        # Собираем путь к задаче
        if (task_path := self._create_task_path()) is None:
            return
        self.task_path = task_path

        if not self._try_load_task_and_update_ui():
            # Если задача не считана или недостоверная задача, разрешаем создать или удалить задачу
            self.set_button_create_active(self.btn_create_task, True)

    def _create_task_path(self) -> str | None:
        """
        Формирует полный путь к задаче планировщика.

        Применяет значения папки и имени задачи к соответствующим UI-контролам,
        получает их текущие значения и, при наличии обоих, собирает путь к задаче.

        Если папка или имя задачи отсутствуют, устанавливает состояние ошибки
        в UI и отключает кнопку создания задачи.

        Returns:
            str | None: Полный путь к задаче или ``None``, если данные некорректны.
        """
        task_folder = self._apply_value_to_widget("task_folder")
        task_name = self._apply_value_to_widget("task_name")

        if not task_folder or not task_name:
            self._set_error_ui_state(C.TEXT_NOT_TASK, btn_create_task_enable=False)
            return None

        # Собираем путь к задаче
        return str(Path(task_folder) / task_name)

    def _try_load_task_and_update_ui(self) -> bool:
        """
        Пытается загрузить задачу планировщика и обновить UI на основе её данных.

        Читает описание еженедельной задачи по пути self.task_path и сохраняет
        результат в self.task_info. В случае ошибки определения задачи
        обрабатывает некорректную конфигурацию, а если задача не найдена —
        переводит UI в соответствующее состояние.

        При успешной загрузке обновляет элементы интерфейса данными задачи.

        Returns:
            True  — если задача успешно загружена и UI обновлён,
            False — если произошла ошибка загрузки.
        """
        try:
            self.task_info = task_scheduler.read_weekly_task(self.task_path)
        except ValueError:
            self._handle_invalid_task_definition()
            return False
        except pywintypes.com_error:
            self._handle_task_not_found()
            return False

        self._update_ui_from_task()
        return True

    def _handle_task_not_found(self) -> None:
        logger.warning(f"Задача {self.task_path} не найдена или недоступна")
        self._update_ui_from_defaults()

    def _handle_invalid_task_definition(self) -> None:
        """Обрабатывает некорректное определение задачи и переводит UI в режим удаления."""
        msg = C.TEXT_TASK_MANUAL_EDIT.format(task=self.task_path)
        logger.error(msg)
        self._set_error_ui_state(msg, btn_create_task_enable=True)
        self._set_task_button_mode("delete")

    def _set_error_ui_state(self, msg: str, btn_create_task_enable: bool) -> None:
        """
        Переводит интерфейс в состояние ошибки.

        Блокирует элементы левой панели, управляет доступностью кнопки
        создания задачи и выводит сообщение об ошибке.
        """
        logger.error(msg)
        self._lock_left_panel_widgets(enable=False)
        self.btn_create_task.setEnabled(btn_create_task_enable)
        self.put_to_info(msg)

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
        self.start_time_task.timeChanged.connect(self.update_buttons_state_enable)
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
          - work_directory
          - description
        """
        self._ui_default = False

        # Описание задачи
        description = self.task_info.get("description")
        if description is not None:
            self._apply_value_to_widget("description", description)

        # Путь к программе
        executable = self.task_info.get("executable")
        if executable is not None:
            self._apply_value_to_widget("program_path", executable)

        # Рабочая папка
        work_directory_path = self.task_info.get("work_directory")
        if work_directory_path is not None:
            self._apply_value_to_widget("work_directory", work_directory_path)

        # Маска дней недели
        self._set_week_mask(self.task_info.get("mask_days"))

        # Время запуска
        start_time = self.task_info.get("start_time")
        if start_time is not None:
            self._apply_value_to_widget("start_time", start_time)

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

        # Установка значений виджетов
        self.parameter_error = False
        self._apply_value_to_widget("description")
        self._apply_value_to_widget("program_path")
        self._apply_value_to_widget_if_present("work_directory")
        self._apply_value_to_widget("mask_of_days")
        self._apply_value_to_widget("start_time")
        self._update_task_creation_ui_state()

    def _update_task_creation_ui_state(self):
        """Обновляет состояние UI в зависимости от готовности задачи к созданию."""
        if self.parameter_error:
            self.put_to_info(C.TASK_NOT_READY_TO_CREATED)
            self._lock_left_panel_widgets(enable=False)
        else:
            self.put_to_info(C.TASK_READY_TO_CREATED)

    def _apply_value_to_widget(
        self,
        key_task_fields: str,
        value: str | None = None,
    ) -> Any | None:
        """
        Контролирует принимаемое значение и, если значение валидно,
        применяет значение к виджету.

        Если value задано, то оно трактуется как готовое значение,
        в противном случае — как имя переменной окружения.

        Возвращает:
            Значение, которое было фактически установлено или None при ошибке.
        """

        field_descr = self.descr_task_fields[key_task_fields]
        final_value = (
            self.env.get_var(field_descr.name_env, field_descr.value_default)
            if value is None
            else value
        )
        if final_value is None:
            return None

        return (
            final_value
            if self._apply_if_valid(field_descr, final_value, value)
            else None
        )

    def _apply_if_valid(
        self, field_descr: DescrTaskFields, final_value: str, value: str | None
    ) -> bool:
        if self.is_valid_value(
            final_value, field_descr.control_type, field_descr.error_text
        ):
            return_text = utils.set_widget_value(
                field_descr.widget, final_value, empty=C.TEXT_EMPTY
            )
            if not return_text:
                return True
            logger.error(f"Ошибка при установке значения {value!r}\n{return_text}")
        return False

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
            self.all_day(checked=False)
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

        # Успешное удаление: Приводим UI к состоянию "Готов к созданию новой задачи"
        self._prepare_ui_for_task_creation()
        return True

    def _prepare_ui_for_task_creation(self):
        """
        Приводит UI в состояние создания новой задачи после удаления существующей.
        """
        # Разблокируем левую панель,
        # возвращаем режим "создания", сбрасываем UI в значения по умолчанию
        self._lock_left_panel_widgets(enable=True)
        self.btn_create_task.setEnabled(True)
        self._set_task_button_mode("create")
        self._update_ui_from_defaults()
        self._ui_dirty = False

    def _lock_left_panel_widgets(self, enable: bool) -> None:
        """
        Включает / отключает все виджеты в левой панели.
        Используется при ошибках конфигурации задачи или при её удалении.
        """
        for child in self.group_box_left.findChildren(QWidget):
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
            raise KeyError(msg)

    def put_to_info(self, message: str, color: str = "red") -> None:
        """
        Выводит сообщение в поле text_info с нужным цветом и насыщенностью шрифта.
        Цвет влияет и на font-weight (успех/ошибка/инфо).
        """
        html_text = utils.make_html(message, color)
        html_text = self.text_to_save_text(html_text)

        self._apply_value_to_widget("info", html_text)

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

        # fmt: off
        return TaskConfig(
            task_path           = self.task_path,
            mask_days           = self.get_week_mask(),
            executable_path     = self.txt_program_path.text(),
            work_directory_path = self.txt_work_directory_path.text(),
            start_time          = self.start_time_task.time().toString("HH:mm"),
            description         = self.txt_task_description.toPlainText(),
        )

    # fmt: on

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

    def text_to_save_text(self, text: str) -> str:
        """Убирает из текста опасный для Qt6 символ"""
        return text.replace("\x00", "")

    def text_handler(self, text: str) -> bool:
        """
        Проверяет текст на отсутствие служебной подстроки C.NULL.

        Возвращает:
            True, если текст не содержит C.NULL, иначе False.
        """
        return C.NULL not in text

    def start_time_handler(self, text: str) -> bool:
        """
        Валидирует время запуска задачи.

        Ожидаемый формат: 'HH:MM'.

        Возвращает:
            True, если строка корректно парсится в QTime, иначе False.
        """
        time = QTime.fromString(text, "HH:mm")
        return time.isValid()

    def task_name_handler(self, name: str) -> bool:
        """
        Проверяет корректность имени задачи планировщика.

        Условия:
            - непустая строка;
            - не начинается и не заканчивается пробелом;
            - не содержит недопустимых символов для имени файла/задачи;
            - длина не более 256 символов.
        """

        # 1. Не пустая строка
        if not isinstance(name, str) or name.strip() == "":
            return False

        # 2. Не начинается и не заканчивается пробелом
        if name[0] == " " or name[-1] == " ":
            return False

        # 3. Проверка недопустимых символов
        if any(ch in INVALID_PATH_CHARACTERS for ch in name):
            return False

        # 4. Проверка длины
        if len(name) > 256:
            return False

        return True

    def task_directory_handler(self, text: str) -> bool:
        return self.directory_handler(text)

    def file_path_handler(self, text: str):
        base = text
        p = Path(text)
        if p.drive:
            base = text[len(p.drive) :]
        # анализуруем путь без драйвера.
        return self.directory_handler(base)

    def directory_handler(self, text: str) -> bool:
        """
        Проверяет корректность (корневого) пути директории в стиле Windows.

        Условия:
            1. Строка не пуста.
            2. Путь является "корневым" (начинается с '\\' или '/').
            3. Каждая часть пути не содержит недопустимых символов/имён.
            4. Путь не заканчивается пробелом или точкой.
        """
        # 1. Проверяем пустое ли имя
        if self.is_empty_string(text):
            return False

        # 2. Проверяем абсолютность пути
        if not self.is_rooted_path(text):
            return False

        # 3, 4. Проверка недопустимых символов и имён для Windows
        if not self.check_parts_for_invalid_chars(text):
            return False

        # 5. Проверка недопустимости завершающих пробела и точки
        if not self.check_trailing_chars(text):
            return False

        return True

    def is_empty_string(self, text: str) -> bool:
        return not isinstance(text, str) or not text

    def is_rooted_path(self, text: str) -> bool:
        return text.startswith(("\\", "/"))

    def check_parts_for_invalid_chars(self, text: str) -> bool:
        p = Path(text[1:])
        for part in p.parts:
            if len(part) > 250:
                return False
            if any(ch in INVALID_PATH_CHARACTERS for ch in part):
                return False
            if any(ord(ch) < 32 for ch in part):
                return False
            if Path(part).stem in RESERVED_DOS_DEVICE_NAMES:
                return False
        return True

    def check_trailing_chars(self, text: str) -> bool:
        return not text.endswith((" ", "."))

    def mask_days_handler(self, text: str) -> bool:
        """
        Проверяет, что строка является корректной двоичной маской дней недели.

        Ожидается строка из '0' и '1', интерпретируемая как целое число
        в диапазоне [0, 255].
        """
        try:
            value = int(text, 2)
        except ValueError, TypeError:
            return False
        return 0 <= value < 256

    def is_valid_value(
        self, value: str, control_type: ControlType, error_text: str
    ) -> bool:
        """
        Универсальная проверка значения по типу контролла.

        Вызывает соответствующий обработчик из get_handlers_map().
        При ошибке логирует сообщение и показывает диалог пользователю.
        """
        handlers = self.get_handlers_map()
        handler = handlers[control_type]
        if not handler(value):
            logger.error(f"{error_text} -> {value}")
            self.parameter_error = True
            self.error_message(error_text, value)
            return False

        return True

    def get_handlers_map(self) -> dict[ControlType, HandlerType]:
        """
        Возвращает отображение ControlType → функция-валидатор.

        Упрощает добавление новых типов полей и соответствующих им обработчиков.
        """
        # fmt: off
        return {
            ControlType.TEXT            : self.text_handler,
            ControlType.START_TIME      : self.start_time_handler,
            ControlType.TASK_NAME       : self.task_name_handler,
            ControlType.TASK_FOLDER     : self.task_directory_handler,
            ControlType.MASK_DAYS       : self.mask_days_handler,
            ControlType.FILE_PATH       : self.file_path_handler,
            ControlType.FOLDER_PATH     : self.file_path_handler,
        }
        # fmt: on

    def _init_descr_task_fields(self) -> None:
        """
        Инициализирует описание полей задачи планировщика.

        Создаёт и заполняет словарь ``self.descr_task_fields``, в котором каждому
        логическому полю задачи сопоставляется объект ``DescrTaskFields``.
        Каждый объект содержит ссылку на атрибут класса, ключ в env,
        тип контроля, сообщение об ошибке и значение по умолчанию (если задано).

        Словарь используется для централизованной валидации, инициализации
        значений и обработки пользовательского ввода.
        """
        self.descr_task_fields: dict[str, DescrTaskFields] = {
            "task_folder": DescrTaskFields(
                self.lbl_task_folder,
                C.TASK_FOLDER,
                ControlType.TASK_FOLDER,
                C.TASK_FOLDER_ERROR,
                C.TASK_FOLDER_DEFAULT,
            ),
            "task_name": DescrTaskFields(
                self.lbl_task_name,
                C.TASK_NAME,
                ControlType.TASK_NAME,
                C.TASK_NAME_ERROR,
                C.TASK_NAME_DEFAULT,
            ),
            "description": DescrTaskFields(
                self.txt_task_description,
                C.TASK_DESCRIPTION,
                ControlType.TEXT,
                C.TASK_DESCRIPTION_ERROR,
                C.TASK_DESCRIPTION_DEFAULT,
            ),
            "program_path": DescrTaskFields(
                self.txt_program_path,
                C.PROGRAM_PATH,
                ControlType.FILE_PATH,
                C.PROGRAM_PATH_ERROR,
                C.PROGRAM_PATH_DEFAULT,
            ),
            "work_directory": DescrTaskFields(
                self.txt_work_directory_path,
                C.WORK_DIRECTORY_PATH,
                ControlType.FOLDER_PATH,
                C.WORK_DIRECTORY_ERROR,
            ),
            "start_time": DescrTaskFields(
                self.start_time_task,
                C.TASK_START_IN,
                ControlType.START_TIME,
                C.START_TASK_ERROR,
                C.START_TASK_DEFAULT,
            ),
            "mask_of_days": DescrTaskFields(
                self.hbox_week_days,
                C.SCHEDULED_DAYS_MASK,
                ControlType.MASK_DAYS,
                C.MASK_ERROR,
                C.MASK_DEFAULT,
            ),
            "info": DescrTaskFields(self.text_info, "", ControlType.TEXT, ""),
        }

    @staticmethod
    def is_absolute_windows_path(p: Path) -> bool:
        # Полноценный абсолютный путь
        if p.is_absolute():
            return True

        # Корневой путь без диска: "\folder"
        # Если путь начинается со слеша — считаем его абсолютным
        if str(p).startswith(("\\", "/")):
            return True

        return False

    def _apply_value_to_widget_if_present(self, widget_name: str):
        field_descr = self.descr_task_fields[widget_name]
        value = self.env.get_var(field_descr.name_env)
        if value:
            self._apply_value_to_widget(widget_name)

    def error_message(self, text: str, informative_text: str) -> None:
        msg = QMessageBox(self._msg_parent())
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Ошибка")
        msg.setText(text)
        msg.setInformativeText(str(informative_text))
        msg.exec()
