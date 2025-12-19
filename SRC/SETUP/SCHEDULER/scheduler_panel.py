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

from typing import Literal

from loguru import logger
from pathlib import Path

from PyQt6.QtWidgets import (
    QPushButton,
    QWidget,
    QCheckBox,
)

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.constants import Constants as C
import SRC.SETUP.SCHEDULER.scheduler_utils as utils
import SRC.SETUP.SCHEDULER.scheduler_dialogs as dialogs
from SRC.SETUP.SCHEDULER.scheduler_button_style import init_button_styles
from SRC.SETUP.SCHEDULER.scheduler_path_selector import ProgramSelector, WorkDirSelector
from SRC.SETUP.SCHEDULER.scheduler_error_formater import ErrorFormater
from SRC.SETUP.SCHEDULER.scheduler_service import TaskSchedulerService
from SRC.SETUP.SCHEDULER.scheduler_dto import TaskConfig
from SRC.SETUP.SCHEDULER.scheduler_panel_ui import HasSchedulePanelUI
from SRC.SETUP.SCHEDULER.scheduler_panel_fields import TaskFieldsController
from SRC.SETUP.SCHEDULER.scheduler_panel_fields import (
    EXCLUDE_UI_KEYS,
    TASK_INFO_KEY_OVERRIDE,
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
        self._ui_default: bool = True  # UI сформировано из значений «по умолчанию»
        self._ui_dirty: bool = False  # пользователем были внесены изменения
        self._ui = ui
        self.parameter_error = False

        self._bind_ui(ui)
        self.fields = TaskFieldsController(ui, dialogs.error_message)
        init_button_styles(self)
        self.error_formatter = ErrorFormater()
        self.scheduler = TaskSchedulerService(self.put_to_info)
        self.env = EnvironmentVariables()
        self._init_ui_from_task_or_default()
        self._init_path_selector()

        # Кнопка создания задачи может менять своё назначение.
        # Сохраняем исходное состояние кнопки создания задачи
        self._default_button_create_task_text = self.btn_create_task.text()
        self._default_button_create_task_slot = self.on_create_or_replace_task

        self._btn_signal_connect()

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

    def _init_ui_from_task_or_default(self) -> None:
        """
        Загружает задачу планировщика (если есть) и обновляет UI.

        Алгоритм:
          1. Получаем папку и имя задачи из переменных окружения (C.TASK_FOLDER, C.TASK_NAME).
          2. Если они не заданы — блокируем левую панель и выводим сообщение.
          3. Пытаемся прочитать WEEKLY-задачу.
          4. При успехе — отражаем параметры задачи в UI.
        """

        # Собираем путь к задаче
        if (task_path := self._create_task_path()) is None:
            return
        self.task_path = task_path

        if not self._try_load_task_and_update_ui():
            # Если задача не считана или недостоверная задача, разрешаем создать или удалить задачу
            self.set_button_create_active(self.btn_create_task, True)

    def _init_path_selector(self):
        self.path_program = ProgramSelector(
            self.txt_program_path, self.btn_path_programm
        )
        self.working_directory = WorkDirSelector(
            self.txt_work_directory_path, self.btn_work_directory
        )

        self.path_program.set_path(self.txt_program_path.text())
        self.working_directory.set_path(self.txt_work_directory_path.text())

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
        task_folder = self.fields.apply_value_to_widget("task_folder")
        task_name = self.fields.apply_value_to_widget("task_name")

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
        task_info, status = self.scheduler.read_weekly_task(self.task_path)
        if status == "invalid_definition":
            self._handle_invalid_task_definition()
            return False
        if status == "not_found":
            self._handle_task_not_found()
            return False

        self.task_info = task_info
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
        self.btn_create_task.clicked.connect(self._default_button_create_task_slot)
        self.btn_reject_changes.clicked.connect(self.on_reject_all_changes)
        self.btn_delete_task.clicked.connect(self.on_delete_task_clicked)

        # Изменения текста / времени / чекбоксов → активировать кнопки «создать»/«отменить»
        self.btn_path_programm.clicked.connect(self.update_buttons_state_enable)
        self.btn_work_directory.clicked.connect(self.update_buttons_state_enable)
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

        for ui_key in self.fields.build_descr_task_fields(ui=self._ui):
            if ui_key in EXCLUDE_UI_KEYS:
                continue

            src_key = TASK_INFO_KEY_OVERRIDE.get(ui_key, ui_key)
            self.fields.apply_value_to_widget(ui_key, self.task_info.get(src_key) or "")

        self._set_week_mask(self.task_info.get("mask_days"))
        self.update_buttons_state(enabled=False)
        self.set_ui_dirty(False, C.TEXT_REJECT_DATA, "green")

    def _update_ui_from_defaults(self) -> None:
        """
        Заполняет UI значениями по умолчанию (из constants / окружения).

        Используется, когда:
          - задача ещё не была создана;
          - задача была удалена;
        """

        self._ui_default = True
        self.set_ui_dirty(False, C.TEXT_REJECT_DATA, "green")

        # Установка значений виджетов
        self.parameter_error = False
        self.fields.apply_value_to_widget("description")
        self.fields.apply_value_to_widget("program_path")
        self.fields.apply_value_to_widget("work_directory")
        self.fields.apply_value_to_widget("mask_of_days")
        self.fields.apply_value_to_widget("start_time")
        self._update_task_creation_ui_state()

    def _update_task_creation_ui_state(self):
        """Обновляет состояние UI в зависимости от готовности задачи к созданию."""
        if self.parameter_error:
            self.put_to_info(C.TASK_NOT_READY_TO_CREATED)
            self._lock_left_panel_widgets(enable=False)
        else:
            self.put_to_info(C.TASK_READY_TO_CREATED)

    def on_select_all_day(self) -> None:
        """Отмечает все дни недели (маска 1111111) и помечает UI как «изменённый»."""
        self.set_ui_dirty(True)
        self.all_day(checked=True)

    def on_clean_all_day(self) -> None:
        """Снимает выделение со всех дней недели и помечает UI как «изменённый»."""
        self.set_ui_dirty(True)
        self.all_day(checked=False)

    def on_create_or_replace_task(self) -> None:
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
        if not dialogs.confirm_delete_task(self._msg_parent):
            return

        try:
            if self.delete_task():
                self.put_to_info(C.TASK_DELETED_SUCSESSFULL, color="green")
                logger.info(C.TASK_DELETED_SUCSESSFULL)
                self.btn_delete_task.setEnabled(False)
        except Exception as e:
            self.report_com_error(e, C.TASK_DELETED_ERROR)

    def delete_task(self) -> bool:
        """
        Удаляет задачу через сервис планировщика и, при успехе,
        приводит UI к состоянию 'задачи нет'.
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
        self.set_ui_dirty(False)

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
            self.btn_create_task.setText(self._default_button_create_task_text)
            self.btn_create_task.clicked.connect(self._default_button_create_task_slot)
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
        html_text = utils.text_to_save_text(html_text)

        self.fields.apply_value_to_widget("info", html_text)

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

        self.set_ui_dirty(True)
        self.update_buttons_state(enabled=True)

    def update_buttons_state(self, *, enabled: bool) -> None:
        """Включает/выключает кнопки 'Создать задачу' и 'Отказаться от изменен.'."""
        self.btn_create_task.setEnabled(enabled)
        self.btn_reject_changes.setEnabled(enabled)

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
        hr, msg, details = self.scheduler.extract_com_error_info(error)

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
        self.set_ui_dirty(False)
        self.update_buttons_state(enabled=False)
        self.put_to_info(C.TASK_CREATED_SUCSESSFULL, color="green")
        logger.info(C.TASK_CREATED_SUCSESSFULL)
        self.btn_delete_task.setEnabled(True)

    def set_ui_dirty(
        self, new_ui_diry: bool, text: str | None = None, color: str | None = None
    ) -> None:
        if new_ui_diry == self._ui_dirty:
            return

        message_text = text if text else C.TEXT_IS_DIRTY
        color_text = color if color else "red"

        self.put_to_info(message_text, color=color_text)

        self._ui_dirty = new_ui_diry
