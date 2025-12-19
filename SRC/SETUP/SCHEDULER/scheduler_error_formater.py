import pywintypes
from typing import Callable
import SRC.SETUP.SCHEDULER.scheduler_win32 as task_scheduler

_HRESULT_MAP = {
    0x80070005: "Отказано в доступе (запустите от имени администратора)",
    0x8004131F: "Задача уже существует",
    0x8004130F: "Неверное определение задачи",
    0x80070002: "Задача не найдена",
    0x80070003: "Путь не найден",
}


class ErrorFormater:
    """
    Форматирование COM-ошибок в человекочитаемый текст.

    Использует карту HRESULT → описания и функцию extract_hresult из
    task_scheduler_win32 для корректного извлечения кода ошибки.
    """

    def __init__(
        self,
        hresult_map: dict[int, str] | None = None,
        extract_result: Callable[
            [pywintypes.com_error] : int
        ] = task_scheduler.extract_hresult,
    ) -> None:
        self._map = hresult_map if hresult_map is not None else _HRESULT_MAP
        self._extract_result = extract_result

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
        hr = self._extract_result(error)

        return self._map.get(
            hr, f"Ошибка COM (HRESULT=0x{hr:08X}). См. лог для деталей."
        )
