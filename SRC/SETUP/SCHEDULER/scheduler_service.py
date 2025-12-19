from typing import Callable
from loguru import logger

import SRC.SETUP.SCHEDULER.scheduler_win32 as task_scheduler
from SRC.SETUP.SCHEDULER.scheduler_dto import TaskConfig
from SRC.GENERAL.constants import Constants as C


class TaskSchedulerService:
    """Тонкая обёртка над task_scheduler для работы через TaskConfig.

    Позволяет SchedulePanel не зависеть напрямую от деталей реализации
    task_scheduler_win32 и облегчает модульное тестирование.
    """

    def __init__(self, put_to_info: Callable[[str, str], None]):
        self._put_to_info = put_to_info

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

    def delete(self, task_path: str) -> task_scheduler.ComError | None:
        """Удаляет задачу по пути task_path, возвращая None или com_error."""
        error = task_scheduler.delete_task_scheduler(task_path)
        if error:
            logger.error(f"{C.TASK_DELETED_ERROR}\n{error}")
            self._put_to_info(C.TASK_DELETED_ERROR, "red")
            return error

        return None
