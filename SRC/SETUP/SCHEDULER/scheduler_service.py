from __future__ import annotations

from typing import Any, Callable, Literal

from loguru import logger
import pywintypes  # type: ignore

import SRC.SETUP.SCHEDULER.scheduler_win32 as task_scheduler
from SRC.SETUP.SCHEDULER.scheduler_dto import TaskConfig
from SRC.GENERAL.constants import Constants as C


ReadWeeklyStatus = Literal["ok", "not_found", "invalid_definition"]


class TaskSchedulerService:
    """Тонкая обёртка над task_scheduler для работы через TaskConfig.

    Позволяет SchedulePanel не зависеть напрямую от деталей реализации
    task_scheduler_win32 и облегчает модульное тестирование.
    """

    def __init__(self, put_to_info: Callable[[str, str], None]):
        self._put_to_info = put_to_info

    def create_or_replace(self, config: TaskConfig) -> task_scheduler.ComError | None:
        """Создаёт/обновляет задачу по конфигурации. Возвращает com_error или None."""
        error = task_scheduler.create_replace_task_scheduler(
            mask_days=config.mask_days,
            task_path=config.task_path,
            executable_path=config.executable_path,
            work_directory_path=config.work_directory_path,
            start_time=config.start_time,
            description=config.description,
        )
        if error:
            logger.error(f"{C.TASK_CREATED_ERROR}\n{error}")
            return error
        return None

    def delete(self, task_path: str) -> task_scheduler.ComError | None:
        """Удаляет задачу по пути task_path, возвращая None или com_error."""
        error = task_scheduler.delete_task_scheduler(task_path)
        if error:
            logger.error(f"{C.TASK_DELETED_ERROR}\n{error}")
            return error
        return None

    def read_weekly_task(self, task_path: str) -> tuple[dict[str, Any] | None, ReadWeeklyStatus]:
        """Читает WEEKLY-задачу и нормализует ошибки для UI-слоя."""
        try:
            task_info = task_scheduler.read_weekly_task(task_path)
            return task_info, "ok"
        except ValueError:
            return None, "invalid_definition"
        except pywintypes.com_error:  # type: ignore[attr-defined]
            return None, "not_found"

    def extract_com_error_info(self, error: Exception) -> tuple[int, str, str]:
        """Прокси к низкоуровневому разбору com_error для логирования."""
        return task_scheduler.extract_com_error_info(error)  # type: ignore[arg-type]
