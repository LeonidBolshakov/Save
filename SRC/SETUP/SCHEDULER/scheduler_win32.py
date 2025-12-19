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
TASK_ACTION_EXEC = 0
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

    parts = [p for p in path.split("\\") if p]
    if not parts:
        raise ValueError(f"Некорректный путь задачи: {task_path!r}")

    folder_path = "\\" + "\\".join(parts[:-1]) if len(parts) > 1 else "\\"
    task_name = parts[-1]
    return folder_path, task_name


def ensure_folder(root: Any, folder_path: str) -> Any:
    """
    Возвращает папку планировщика, создавая недостающие уровни.

    Проходит по сегментам пути ``folder_path`` относительно папки ``root``.
    Если очередная подпапка не существует, она создаётся. В результате
    возвращается объект папки, соответствующий конечному пути.

    Args:
        root: Объект корневой папки планировщика задач (ITaskFolder),
            относительно которого создаётся/ищется путь
        folder_path (str): Абсолютный путь папки в планировщике
            (например: ``"\\Folder\\SubFolder"``).

    Returns:
        Объект папки планировщика (ITaskFolder), соответствующий ``folder_path``.
    """
    if not folder_path:
        return root

    current = root
    for part in folder_path.strip("\\").split("\\"):
        if not part:
            continue
        try:
            current = current.GetFolder(part)
        except pywintypes.com_error:
            current = current.CreateFolder(part, "")
    return current


def set_weekly_trigger(task_def, days_mask: int, start_time: str) -> None:
    """
    Добавляет WEEKLY-триггер на указанные дни в заданное время.
    start_time: "HH:MM"
    """
    while task_def.Triggers.Count > 0:
        task_def.Triggers.Remove(1)

    trigger = task_def.Triggers.Create(TASK_TRIGGER_WEEKLY)

    today = datetime.now().date().strftime("%Y-%m-%d")  # ISO формат
    trigger.StartBoundary = f"{today}T{start_time}:00"
    trigger.WeeksInterval = 1
    trigger.DaysOfWeek = mask_to_scheduler_days(days_mask)
    trigger.Enabled = True


def set_exec_action(
    task_def: Any,
    executable_path: str,
    work_directory_path: str,
) -> None:
    """
    Добавляет EXEC-действие в определение задачи планировщика.

    Создаёт действие типа TASK_ACTION_EXEC и настраивает запуск
    указанного исполняемого файла без аргументов. При необходимости
    задаёт рабочую директорию процесса.

    Args:
        task_def: COM-объект определения задачи планировщика
            (ITaskDefinition).
        executable_path: Абсолютный путь к исполняемому файлу.
        work_directory_path: Рабочая директория процесса
            (может быть пустой строкой).
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
        scheduler = _connect_scheduler()

        root = scheduler.GetFolder("\\")
        folder_path, task_name = split_task_path(task_path)
        folder = root.GetFolder(folder_path)
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

    В противном случае выбрасывается ValueError
    При отсутствии задачи выбрасывает pywintypes.com_error.
    """
    task = _get_task_from_scheduler(task_path)
    definition = task.Definition

    trigger = _get_single_weekly_trigger(definition, task_path)
    action = _get_single_exec_action(definition, task_path)

    # WEEKLY-триггер
    mask_days = scheduler_days_to_mask(trigger.DaysOfWeek)

    sb = trigger.StartBoundary  # ожидаем формат "YYYY-MM-DDTHH:MM:SS..."
    start_time = sb[11:16] if isinstance(sb, str) and len(sb) >= 16 else None

    executable = action.Path
    work_directory = action.WorkingDirectory
    return {
        "task_path": task_path,
        "mask_days": mask_days,
        "start_time": start_time,
        "executable": executable,
        "work_directory": work_directory if work_directory else None,
        "description": definition.RegistrationInfo.Description,
    }


def _get_task_from_scheduler(task_path: str) -> Any:
    """
    Возвращает задачу планировщика Windows по полному пути.

    Подключается к службе планировщика, извлекает задачу из указанной папки
    и возвращает её COM-объект.

    Args:
        task_path (str): Полный путь к задаче.

    Raises:
        pywintypes.com_error: Если папка или задача не найдены либо произошла
            ошибка COM.
        ValueError: Если путь задачи имеет некорректный формат.
    """
    scheduler = _connect_scheduler()
    root = scheduler.GetFolder("\\")

    folder_path, task_name = split_task_path(task_path)
    folder = root.GetFolder(folder_path)
    return folder.GetTask(task_name)


def _get_single_weekly_trigger(definition: Any, task_path: str) -> Any:
    """
    Возвращает единственный WEEKLY-триггер задачи.

    Проверяет, что определение задачи содержит ровно один триггер и
    что его тип — WEEKLY. В противном случае выбрасывает ValueError.

    Args:
        definition: COM-объект определения задачи планировщика
            (ITaskDefinition)
        task_path (str): Путь задачи, используется в сообщениях об ошибках.

    Returns:
        COM-объект триггера планировщика (IWeeklyTrigger).

    Raises:
        ValueError: Если количество триггеров не равно одному
            или тип триггера отличается от WEEKLY.
    """
    triggers = list(definition.Triggers)
    if len(triggers) != 1:
        raise ValueError(
            f"Задача {task_path!r} должна содержать ровно один триггер, "
            f"найдено: {len(triggers)} тригера."
        )

    trigger = triggers[0]
    if trigger.Type != TASK_TRIGGER_WEEKLY:
        raise ValueError(
            f"Задача {task_path!r} должна иметь WEEKLY-триггер, "
            f"но найден Type={trigger.Type}-тригер."
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
            f"найдено: {len(actions)} действия."
        )

    action = actions[0]

    if action.Type != TASK_ACTION_EXEC:
        raise ValueError(
            f"Ожидалось EXEC-действие (TASK_ACTION_EXEC), "
            f"но найдено Type={action.Type}-действие."
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
        scheduler = _connect_scheduler()
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


def _connect_scheduler() -> Any:
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
