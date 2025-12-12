"""
Task Scheduler Win32/COM API wrapper.

Этот модуль обеспечивает минималистичную, надёжную и предсказуемую обёртку
над Windows Task Scheduler через win32com.client (Schedule.Service).

Возможности:
- создание и обновление WEEKLY-задач;
- чтение существующих задач;
- преобразование внутренних битовых масок дней недели в DaysOfWeek API;
- корректное извлечение HRESULT (включая внутренний COM HRESULT);
- функции-помощники для настройки триггеров и действий.

Использует только Win32 COM API. Не зависит от XML или schtasks.exe.
Подходит для GUI-приложений, где требуется строгий контроль ошибок.

Автор задачи: Большаков Л.А. # noqa
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypeAlias

import win32com.client
import pywintypes

ComError: TypeAlias = pywintypes.com_error  # type: ignore[attr-defined]

# 7-битная маска дней: bit0 = MON, ..., bit6 = SUN
MASK_ALL_DAYS = 0b1111111

# Task Scheduler constants
TASK_TRIGGER_WEEKLY = 3
TASK_CREATE_OR_UPDATE = 6
TASK_LOGON_INTERACTIVE_TOKEN = 3

# Metadata
TASK_AUTHOR = "Большаков Л.А."  # noqa


def mask_to_scheduler_days(mask: int) -> int:
    """Внутренняя маска (bit0=MON - bit6=SUN) -> DaysOfWeek (bit0=SUN - bit6=SAT)."""
    m = mask & MASK_ALL_DAYS
    return ((m << 1) & MASK_ALL_DAYS) | ((m >> 6) & 1)


def scheduler_days_to_mask(days_of_week: int) -> int:
    """DaysOfWeek (bit0=SUN - bit6=SAT) -> внутренняя маска (bit0=MON - bit6=SUN)."""
    v = days_of_week & MASK_ALL_DAYS
    return (v >> 1) | ((v & 1) << 6)


def split_task_path(task_path: str) -> tuple[str, str]:
    """
    Делит путь задачи на (folder_path, task_name).

    Примеры:
        "MyTask"          -> ("\\", "MyTask")
        "\\Folder\\Task"  -> ("\\Folder", "Task")
    """
    path = task_path.replace("/", "\\").strip()
    if not path.startswith("\\"):
        path = "\\" + path

    parts = [p for p in path.split("\\") if p]
    if not parts:
        raise ValueError(f"Некорректный путь задачи: {task_path!r}")

    folder_path = "\\" + "\\".join(parts[:-1]) if len(parts) > 1 else "\\"
    task_name = parts[-1]
    return folder_path, task_name


def ensure_folder(root, folder_path: str):
    """
    Возвращает папку планировщика, создавая недостающие уровни.
    """
    if folder_path == "\\":
        return root

    current = root
    for part in folder_path.strip("\\").split("\\"):
        if not part:
            continue
        try:
            current = current.GetFolder(part)
        except Exception:
            current = current.CreateFolder(part, "")
    return current


def set_weekly_trigger(task_def, days_mask: int, start_time: str) -> None:
    """
    Добавляет WEEKLY-триггер на указанные дни в заданное время.
    start_time: "HH:MM"
    """
    trigger = task_def.Triggers.Create(TASK_TRIGGER_WEEKLY)

    today = datetime.now().date().strftime("%Y-%m-%d")  # ISO формат
    trigger.StartBoundary = f"{today}T{start_time}:00"
    trigger.WeeksInterval = 1
    trigger.DaysOfWeek = mask_to_scheduler_days(days_mask)
    trigger.Enabled = True


def set_exec_action(task_def, executable_path: str, work_directory_path: str) -> None:
    """
    Добавляет EXEC-действие: запуск executable_path без аргументов и
    установку рабочей директории.

    Args:
        task_def: Объект TaskDefinition.
        executable_path: Путь к исполняемому файлу.
        work_directory_path: Рабочая директория для процесса (может быть пустой).
    """
    action = task_def.Actions.Create(0)  # TASK_ACTION_EXEC = 0

    # Установка выполняемого файла
    action.Path = executable_path

    # Установка рабочей директории.
    if work_directory_path:
        try:
            action.WorkingDirectory = work_directory_path
        except (AttributeError, ValueError, pywintypes.com_error) as e:
            raise pywintypes.com_error


def delete_task_scheduler(task_path: str) -> ComError | None:
    """
    Удаляет задачу из Windows Task Scheduler (Win32 COM API).

    Поведение:
        - task_path может быть как "MyTask", так и "\\Folder\\MyTask";
        - если задача не найдена или возникает COM-ошибка — возвращается pywintypes.com_error;
        - другие исключения (ValueError из split_task_path и т.п.) пробрасываются.

    Возвращает:
        None — при успешном удалении;
        pywintypes.com_error — при ошибке COM.
    """
    try:
        scheduler = win32com.client.Dispatch("Schedule.Service")
        scheduler.Connect()

        root = scheduler.GetFolder("\\")
        folder_path, task_name = split_task_path(task_path)
        folder = root.GetFolder(folder_path)

        # DeleteTask(Name, flags). flags = 0
        folder.DeleteTask(task_name, 0)

        return None

    except pywintypes.com_error as e:  # type: ignore[attr-defined]
        return e


def read_weekly_task(task_path: str) -> dict[str, Any]:
    """
    Читает WEEKLY-задачу планировщика и возвращает её параметры.

    Возвращаемый dict:
      - task_path       : исходный путь задачи;
      - mask_days       : внутренняя маска дней (bit0=MON — bit6=SUN);
      - start_time      : строка "HH:MM" или None;
      - executable      : путь к EXE или None;
      - work_dictonary  : рабочая директория;
      - description     : описание задачи.

    Требования:
      — у задачи должен быть ровно один триггер;
      — этот триггер обязан быть WEEKLY;
      — у задачи должно быть ровно одно действие;
      — это действие должно быть EXEC.

    В противном случае выбрасывается ValueError.
    """
    task = _get_task_from_scheduler(task_path)
    definition = task.Definition

    trigger = _get_single_weekly_trigger(definition, task_path)
    action = _get_single_exec_action(definition, task_path)

    # WEEKLY-триггер
    mask_days = scheduler_days_to_mask(trigger.DaysOfWeek)
    start_time: str | None = None

    sb = trigger.StartBoundary  # ожидаем формат "YYYY-MM-DDTHH:MM:SS..."
    if isinstance(sb, str) and len(sb) >= 16:
        start_time = sb[11:16]  # "HH:MM"

    executable = getattr(action, "Path", None)
    work_directory = getattr(action, "WorkDirectory", None)
    return {
        "task_path": task_path,
        "mask_days": mask_days,
        "start_time": start_time,
        "executable": executable,
        "work_directory": work_directory,
        "description": definition.RegistrationInfo.Description,
    }


def _get_task_from_scheduler(task_path: str) -> Any:
    scheduler = win32com.client.Dispatch("Schedule.Service")
    scheduler.Connect()
    root = scheduler.GetFolder("\\")

    folder_path, task_name = split_task_path(task_path)
    folder = root.GetFolder(folder_path)
    return folder.GetTask(task_name)


def _get_single_weekly_trigger(definition, task_path: str):
    """Возвращает единственный WEEKLY-триггер или бросает ValueError."""
    triggers = list(definition.Triggers)
    if len(triggers) != 1:
        raise ValueError(
            f"Задача {task_path!r} должна содержать ровно один триггер, "
            f"найдено: {len(triggers)}."
        )

    trigger = triggers[0]
    if trigger.Type != TASK_TRIGGER_WEEKLY:
        raise ValueError(
            f"Задача {task_path!r} должна иметь WEEKLY-триггер, "
            f"но найден Type={trigger.Type}."
        )

    return trigger


def _get_single_exec_action(
    definition: win32com.client.CDispatch, task_path: str
) -> win32com.client.CDispatch:
    """Возвращает единственное EXEC-действие или бросает ValueError."""
    actions = list(definition.Actions)
    if len(actions) != 1:
        raise ValueError(
            f"Задача {task_path!r} должна содержать ровно одно действие, "
            f"найдено: {len(actions)}."
        )

    action = actions[0]

    # TASK_ACTION_EXEC == 0
    if action.Type != 0:
        raise ValueError(
            f"Ожидалось EXEC-действие (TASK_ACTION_EXEC), "
            f"но найдено Type={action.Type}."
        )

    return action


def extract_hresult(error: pywintypes.com_error) -> int:  # type: ignore[attr-defined]
    """Возвращает корректный HRESULT (учитывая вложенный COM HRESULT)."""
    outer = error.args[0] if error.args else 0
    inner = None
    if (
        len(error.args) > 2
        and isinstance(error.args[2], tuple)
        and len(error.args[2]) >= 6
    ):
        raw = error.args[2][5]
        if isinstance(raw, int):
            inner = raw
    return (inner if inner is not None else outer) & 0xFFFFFFFF


def extract_com_error_info(error: pywintypes.com_error) -> tuple[int, str, str]:  # type: ignore[attr-defined]
    """
    Возвращает:
      (hresult, message, details)
    """
    hr = extract_hresult(error)

    msg = error.args[1] if len(error.args) > 1 else ""
    details = error.args[2] if len(error.args) > 2 else ""

    return hr, msg, details


from typing import Any, Tuple


def create_replace_task_scheduler(
    *,
    mask_days: int,
    task_path: str,
    executable_path: str,
    work_directory_path: str,
    start_time: str,
    description: str,
) -> ComError | None:
    """
    Создаёт или заменяет WEEKLY-задачу в Windows Task Scheduler (Win32 COM API).

    Возвращает:
        None — при успехе,
        pywintypes.com_error — при COM-ошибке.
    """
    try:
        scheduler = _create_scheduler()
        target_folder, task_name = _get_target_folder_and_name(scheduler, task_path)
        task_def = _build_task_definition(
            scheduler=scheduler,
            description=description,
            mask_days=mask_days,
            start_time=start_time,
            executable_path=executable_path,
            work_directory_path=work_directory_path,
        )
        _register_task(target_folder, task_name, task_def)
        return None

    except pywintypes.com_error as e:  # type: ignore[attr-defined]
        return e


# ----------------- helpers -----------------


def _create_scheduler() -> Any:
    """Создаёт и подключает COM-объект планировщика."""
    scheduler = win32com.client.Dispatch("Schedule.Service")
    scheduler.Connect()
    return scheduler


def _get_root_folder(scheduler: Any) -> Any:
    """Возвращает корневую папку планировщика задач."""
    return scheduler.GetFolder("\\")


def _get_target_folder_and_name(scheduler: Any, task_path: str) -> Tuple[Any, str]:
    """
    По полному пути задачи возвращает целевую папку и имя задачи.
    """
    root = _get_root_folder(scheduler)
    folder_path, task_name = split_task_path(task_path)
    target_folder = ensure_folder(root, folder_path)
    return target_folder, task_name


def _build_task_definition(
    *,
    scheduler: Any,
    description: str,
    mask_days: int,
    start_time: str,
    executable_path: str,
    work_directory_path: str,
) -> Any:
    """
    Создаёт и настраивает TaskDefinition:
    регистрационная информация, общие настройки, триггер и действие.
    """
    task_def = scheduler.NewTask(0)

    _configure_registration_info(task_def, description)
    _configure_basic_settings(task_def)
    set_weekly_trigger(task_def, mask_days, start_time)
    set_exec_action(task_def, executable_path, work_directory_path)

    return task_def


def _configure_registration_info(task_def: Any, description: str) -> None:
    """Заполняет RegistrationInfo задачи."""
    task_def.RegistrationInfo.Description = description
    task_def.RegistrationInfo.Author = TASK_AUTHOR


def _configure_basic_settings(task_def: Any) -> None:
    """Настраивает базовые свойства задачи (включена, поведение при старте, питание)."""
    settings = task_def.Settings
    settings.Enabled = True
    settings.StartWhenAvailable = True
    settings.DisallowStartIfOnBatteries = False


def _register_task(target_folder: Any, task_name: str, task_def: Any) -> None:
    """Регистрирует (создаёт или обновляет) задачу в указанной папке."""
    target_folder.RegisterTaskDefinition(
        task_name,
        task_def,
        TASK_CREATE_OR_UPDATE,
        "",
        "",
        TASK_LOGON_INTERACTIVE_TOKEN,
    )
