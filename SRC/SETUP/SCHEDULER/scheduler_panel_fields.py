from loguru import logger
from typing import Any, Callable

from SRC.SETUP.SCHEDULER.scheduler_panel_ui import ControlType
import SRC.SETUP.SCHEDULER.schedule_validators as validators
from SRC.SETUP.SCHEDULER.scheduler_panel_ui import (
    HandlerType,
    DescrTaskFields,
    HasSchedulePanelUI,
)
import SRC.SETUP.SCHEDULER.scheduler_utils as utils
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.environment_variables import EnvironmentVariables

EXCLUDE_UI_KEYS = {"info", "mask_of_days", "task_folder", "task_name"}
TASK_INFO_KEY_OVERRIDE = {
    "program_path": "executable",
}
ErrorSinc = Callable[[str, str], None]


class TaskFieldsController:
    def __init__(
        self,
        ui: HasSchedulePanelUI,
        on_error: ErrorSinc,
    ):
        self._ui = ui
        self._fields = self.build_descr_task_fields(ui)
        self._on_error = on_error
        self.env = EnvironmentVariables()

    def get_handlers_map(self) -> dict[ControlType, HandlerType]:
        """
        Возвращает отображение ControlType → функция-валидатор.

        Упрощает добавление новых типов полей и соответствующих им обработчиков.
        """
        # fmt: off
        return {
            ControlType.TEXT            : validators.text_handler,
            ControlType.START_TIME      : validators.start_time_handler,
            ControlType.TASK_NAME       : validators.task_name_handler,
            ControlType.TASK_FOLDER     : validators.task_directory_handler,
            ControlType.MASK_DAYS       : validators.mask_days_handler,
            ControlType.FILE_PATH       : validators.file_path_handler,
            ControlType.FOLDER_PATH     : validators.file_path_handler,
        }
        # fmt: on

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
            # self.parameter_error = True
            self._on_error(error_text, value)
            return False

        return True

    def build_descr_task_fields(
        self, ui: HasSchedulePanelUI
    ) -> dict[str, DescrTaskFields]:
        """
        Инициализирует описание полей задачи планировщика.

        Создаёт и возвращает словарь, в котором каждому
        логическому полю задачи сопоставляется объект ``DescrTaskFields``.
        Каждый объект содержит ссылку на атрибут класса, ключ в env,
        тип контроля, сообщение об ошибке и значение по умолчанию (если задано).

        Словарь используется для централизованной валидации, инициализации
        значений и обработки пользовательского ввода.
        """
        descr_task_fields: dict[str, DescrTaskFields] = {
            "task_folder": DescrTaskFields(
                ui.label_task_location,
                C.TASK_FOLDER,
                ControlType.TASK_FOLDER,
                C.TASK_FOLDER_ERROR,
                C.TASK_FOLDER_DEFAULT,
            ),
            "task_name": DescrTaskFields(
                ui.label_task_name,
                C.TASK_NAME,
                ControlType.TASK_NAME,
                C.TASK_NAME_ERROR,
                C.TASK_NAME_DEFAULT,
            ),
            "description": DescrTaskFields(
                ui.textEdit_task_description,
                C.TASK_DESCRIPTION,
                ControlType.TEXT,
                C.TASK_DESCRIPTION_ERROR,
                C.TASK_DESCRIPTION_DEFAULT,
            ),
            "program_path": DescrTaskFields(
                ui.lineEdit_path_programm,
                C.PROGRAM_PATH,
                ControlType.FILE_PATH,
                C.PROGRAM_PATH_ERROR,
                C.PROGRAM_PATH_DEFAULT,
            ),
            "work_directory": DescrTaskFields(
                ui.lineEdit_path_work_directory,
                C.WORK_DIRECTORY_PATH,
                ControlType.FOLDER_PATH,
                C.WORK_DIRECTORY_ERROR,
            ),
            "start_time": DescrTaskFields(
                ui.timeEdit_task_start_in,
                C.TASK_START_IN,
                ControlType.START_TIME,
                C.START_TASK_ERROR,
                C.START_TASK_DEFAULT,
            ),
            "mask_of_days": DescrTaskFields(
                ui.hbox_week_days,
                C.SCHEDULED_DAYS_MASK,
                ControlType.MASK_DAYS,
                C.MASK_ERROR,
                C.MASK_DEFAULT,
            ),
            "info": DescrTaskFields(
                ui.textEdit_Error,
                "",
                ControlType.TEXT,
                "",
            ),
        }

        return descr_task_fields

    def apply_value_to_widget(
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
        field_descr = self._fields[key_task_fields]
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
