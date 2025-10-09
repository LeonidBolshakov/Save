from __future__ import annotations

from typing import Any, Literal, Iterable

import pywintypes  # type: ignore[import-not-found]
import pythoncom  # type: ignore[import-not-found]
import win32com.client as win32  # type: ignore[import-not-found]

from SRC.SETUP.parsers import parse_actions, parse_triggers  # type: ignore[import-not-found]

# Распространённые HRESULT коды, встречающиеся при работе с планировщиком
_HR_NOT_FOUND = -2147024894  # 0x80070002: Система не может найти указанный файл
_HR_DENIED = -2147024891  # 0x80070005: Отказано в доступе


def _extract_hresult(ex: pywintypes.com_error) -> int | None:  # type: ignore[name-defined]
    """
    Достаём максимально «полезный» HRESULT из pywin32-исключения.
    При DISPATCH-обёртке (-2147352567) пытаемся найти вложенный код из details.
    """
    args = getattr(ex, "args", None)
    if not args:
        return None

    # 1) Прямой int в args[0]
    a0 = args[0]
    if isinstance(a0, int):
        # Если это общая обёртка DISP_E_EXCEPTION, попробуем раскопать глубже
        if a0 != -2147352567:  # 0x80020009
            return a0

    # 2) pywin32-style: (hresult, text, details, help)
    # details обычно кортеж, последний элемент — inner HRESULT (например, -2147024894)
    if len(args) >= 3:
        details = args[2]
        if isinstance(details, (tuple, list)) and details:
            # Берём последний int внутри details
            tail = details[-1]
            if isinstance(tail, int):
                return tail

    # 3) Запасной вариант: пробежаться по всем вложенным значениям и взять первый int
    def _walk(x) -> Iterable[int]:
        if isinstance(x, int):
            yield x
        elif isinstance(x, (tuple, list)):
            for y in x:
                yield from _walk(y)

    for val in _walk(args):
        return val  # первый найденный int
    return None


def _classify_hr(hr: int | None) -> Literal["not_found", "denied", "other"]:
    """
    Нормализует HRESULT к простым категориям ошибок.
    """
    if hr == _HR_NOT_FOUND:
        return "not_found"
    if hr == _HR_DENIED:
        return "denied"
    return "other"


def _dispatch_service() -> Any:
    """
    Создаёт COM-объект службы планировщика.
    """
    try:
        return win32.gencache.EnsureDispatch("Schedule.Service2")  # type: ignore
    except pywintypes.com_error as ex:  # type: ignore[name-defined]
        hr = _extract_hresult(ex)
        raise RuntimeError(f"Schedule.Service не создан, HRESULT={hr}") from None
