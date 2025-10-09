"""
Модуль parsers.py — парсинг свойств задач Планировщика Windows (triggers и actions).

Содержит:
- Перечисления типов триггеров и действий (TriggerType, ActionType).
- Функции разбора COM-объектов триггеров (_parse_daily и др.).
- Функции разбора действий (_parse_exec и др.).
- Функции разбора parse_triggers и parse_actions.
"""

from __future__ import annotations
from enum import IntEnum
from typing import Any
import win32com.client as win32  # type: ignore


class TriggerType(IntEnum):
    """Типы триггеров Планировщика (минимальный набор)."""

    # fmt: off
    DAILY =       2  # Ежедневный запуск; интерфейс IDailyTrigger
    WEEKLY =      3  # По дням недели с интервалом недель; IWeeklyTrigger
    MONTHLY =     4  # По датам месяца и месяцам; IMonthlyTrigger
    MONTHLY_DOW = 5  # По «n-й день недели» каждого месяца; IMonthlyDOWTrigger
    BOOT =        7  # При старте ОС; IBootTrigger
    LOGON =       8  # При входе пользователя; ILogonTrigger
    # fmt: on


class ActionType(IntEnum):
    """Типы действий Планировщика (минимальный набор)."""

    # fmt: off
    EXEC        = 0  # Запуск исполняемого файла/скрипта; IExecAction
    COM_HANDLER = 5  # Вызов COM-обработчика; IComHandlerAction
    # fmt: on


def _get_str(o: Any, name: str, default: str | None = "") -> str | None:
    """Безопасно получить str атрибут COM-объекта с запасным значением."""
    attr = getattr(o, name, default)
    return attr if isinstance(attr, str) else default


def _get_bool(o: Any, name: str, default: bool = False) -> bool:
    """Безопасно получить bool атрибут COM-объекта с запасным значением."""
    attr = getattr(o, name, default)
    return attr if isinstance(attr, bool) else default


def _get_int(o: Any, name: str, default: int = 0) -> int:
    """Безопасно получить int атрибут COM-объекта с запасным значением."""
    attr = getattr(o, name, default)
    return attr if isinstance(attr, int) else default


def _rep_dict(rep: Any) -> dict[str, Any]:
    """Преобразует объект Repetition в словарь (интервал, длительность и тд.)."""
    if not rep:
        return {}
    # fmt: off
    return {
        "Период повторения":                _get_str(rep, "Interval", None),
        "Длительность окна":                _get_str(rep, "Duration", None),
        "Останавливать по окончании окна":  _get_bool(rep, "StopAtDurationEnd", False),
    }


# fmt: on


# ---- Триггеры ----
def _parse_daily(trg: Any) -> dict[str, Any]:
    """Разобрать ежедневный триггер (IDailyTrigger)."""
    d = win32.CastTo(trg, "IDailyTrigger")
    # fmt: off
    res = {
        "Тип":              "Daily",
        "Интервал (дней)":  _get_int(d, "DaysInterval", 0),
        "Начало":           _get_str(d, "StartBoundary", None),
        "Окончание":        _get_str(d, "EndBoundary", None),
        "Включён":          _get_bool(d, "Enabled", True),
    }
    # fmt: on
    res.update(_rep_dict(_get_str(d, "Repetition", None)))
    return res


def _parse_weekly(trg: Any) -> dict[str, Any]:
    """Разобрать еженедельный триггер (IWeeklyTrigger)."""
    w = win32.CastTo(trg, "IWeeklyTrigger")
    # fmt: off
    res = {
        "Тип":                  "Weekly",
        "Интервал (недель)":    _get_int(w, "WeeksInterval", 0),
        "Дни недели":           _get_int(w, "DaysOfWeek", 0),
        "Начало":               _get_str(w, "StartBoundary", None),
        "Окончание":            _get_str(w, "EndBoundary", None),
        "Включён":              _get_bool(w, "Enabled", True),
    }
    # fmt: on
    res.update(_rep_dict(_get_str(w, "Repetition", None)))
    return res


def _parse_monthly(trg: Any) -> dict[str, Any]:
    """Разобрать ежемесячный триггер по датам (IMonthlyTrigger)."""
    m = win32.CastTo(trg, "IMonthlyTrigger")
    # fmt: off
    res = {
        "Тип":          "Monthly",
        "Дни месяца":   _get_int(m, "DaysOfMonth", 0),
        "Месяцы":       _get_int(m, "MonthsOfYear", 0),
        "Начало":       _get_str(m, "StartBoundary", None),
        "Окончание":    _get_str(m, "EndBoundary", None),
        "Включён":      _get_bool(m, "Enabled", True),
    }
    # fmt: on
    res.update(_rep_dict(_get_str(m, "Repetition", None)))
    return res


def _parse_monthly_dow(trg: Any) -> dict[str, Any]:
    """Разобрать ежемесячный триггер по дням недели (IMonthlyDOWTrigger)."""
    md = win32.CastTo(trg, "IMonthlyDOWTrigger")
    # fmt: off
    res = {
        "Тип":          "MonthlyDOW",
        "Неделя":       _get_int(md, "WeeksOfMonth", 0),
        "Дни недели":   _get_int(md, "DaysOfWeek", 0),
        "Месяцы":       _get_int(md, "MonthsOfYear", 0),
        "Начало":       _get_str(md, "StartBoundary", None),
        "Окончание":    _get_str(md, "EndBoundary", None),
        "Включён":      _get_bool(md, "Enabled", True),
    }
    # fmt: on
    res.update(_rep_dict(_get_str(md, "Repetition", None)))
    return res


def _parse_logon(trg: Any) -> dict[str, Any]:
    """Разобрать триггер при входе пользователя (ILogonTrigger)."""
    lg = win32.CastTo(trg, "ILogonTrigger")
    # fmt: off
    res = {
        "Тип":          "AtLogon",
        "Пользователь": _get_str(lg, "UserId", None),
        "Начало":       _get_str(lg, "StartBoundary", None),
        "Окончание":    _get_str(lg, "EndBoundary", None),
        "Включён":      _get_bool(lg, "Enabled", True),
    }
    # fmt:on
    res.update(_rep_dict(_get_str(lg, "Repetition", None)))
    return res


def _parse_boot(trg: Any) -> dict[str, Any]:
    """Разобрать триггер при загрузке ОС (IBootTrigger)."""
    b = win32.CastTo(trg, "IBootTrigger")
    # fmt: off
    res = {
        "Тип":          "AtStartup",
        "Начало":       _get_str(b, "StartBoundary", None),
        "Окончание":    _get_str(b, "EndBoundary", None),
        "Включён":      _get_bool(b, "Enabled", True),
    }
    # fmt: on
    res.update(_rep_dict(_get_str(b, "Repetition", None)))
    return res


# Диспетчер типов триггеров → функция разбора
# fmt: off
_TRG_DISPATCH = {
    TriggerType.DAILY: _parse_daily,              # Ежедневный триггер → IDailyTrigger
    TriggerType.WEEKLY: _parse_weekly,            # Еженедельный триггер → IWeeklyTrigger
    TriggerType.MONTHLY: _parse_monthly,          # Ежемесячный по датам → IMonthlyTrigger
    TriggerType.MONTHLY_DOW: _parse_monthly_dow,  # Ежемесячный по дням недели → IMonthlyDOWTrigger
    TriggerType.LOGON: _parse_logon,              # При входе пользователя → ILogonTrigger
    TriggerType.BOOT: _parse_boot,                # При старте ОС → IBootTrigger
}
# fmt: on


def parse_triggers(definition: Any) -> list[dict[str, Any]]:
    """
    Разобрать все триггеры из Definition задачи.

    Args:
        definition: COM-объект TaskDefinition.
    Returns:
        Список словарей с параметрами триггеров.
    """
    out: list[dict[str, Any]] = []
    for trg in definition.Triggers:
        t_val = _get_int(trg, "Type", -1)
        try:
            fn = _TRG_DISPATCH.get(TriggerType(t_val))
        except ValueError:
            fn = None
        out.append(
            fn(trg)
            if fn
            else {"Тип": f"UNKNOWN_{t_val}", "raw_type": t_val, "raw": str(trg)}
        )
    return out


# ---- Действия ----
def _parse_exec(act: Any) -> dict[str, Any]:
    """Разобрать Exec-действие (запуск программы)."""
    # fmt: off
    return {
        "Тип":              "Exec",
        "Описание":         "Запуск программы",
        "Имя программы":    _get_str(act, "Path", "") or "",
        "Аргументы":        _get_str(act, "Arguments", "") or "",
        "Рабочая папка":    _get_str(act, "WorkingDirectory", "") or "",
    }


# fmt: on


def _parse_com_handler(act: Any) -> dict[str, Any]:
    """Разобрать ComHandler-действие."""
    return {"Тип": "ComHandler", "Описание": "COM-действие"}


_ACT_DISPATCH = {
    ActionType.EXEC: _parse_exec,
    ActionType.COM_HANDLER: _parse_com_handler,
}


def parse_actions(definition: Any) -> list[dict[str, Any]]:
    """
    Разобрать все действия из Definition задачи.

    Args:
        definition: COM-объект TaskDefinition.
    Returns:
        Список словарей с параметрами действий.
    """
    out: list[dict[str, Any]] = []

    for act in definition.Actions:
        a_val = _get_int(act, "Type", -999)
        member = ActionType._value2member_map_.get(a_val)

        if member is None:
            out.append(
                {
                    "Тип": str(a_val),
                    "Описание": "Неизвестный или устаревший тип действия",
                }
            )
            continue

        key: ActionType | None
        try:
            key = ActionType(a_val)
        except ValueError:
            key = None

        if key is not None:
            fn = _ACT_DISPATCH.get(key)
        else:
            fn = None

        if fn is None:
            out.append(
                {
                    "Тип": member.name,
                    "Описание": "Нет обработчика для этого типа действия",
                }
            )
            continue

        try:
            out.append(fn(act))
        except Exception as e:
            out.append(
                {
                    "Тип": member.name,
                    "Описание": "Ошибка разбора действия",
                    "Ошибка": str(e),
                }
            )

    return out
