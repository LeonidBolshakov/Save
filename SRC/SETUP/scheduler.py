"""
Scheduler — адаптер над COM‑планировщиком задач Windows (Task Scheduler).

Назначение
---------
Предоставить компактный и предсказуемый API для типичных операций с задачами:
создание и обновление (одно Exec‑действие + один Weekly‑триггер), чтение и удаление.

Ключевые идеи
-------------
1) Ранние проверки и единая классификация HRESULT → понятные Python‑исключения.
2) DTO‑слой через @dataclass TaskInfo для безопасной передачи данных наружу.
3) Тонкие помощники (_get_folder, _get_task, _register_update) вместо длинных
   монолитных методов.

Зависимости
-----------
- pywin32: win32com.client, pywintypes, pythoncom
- внутренние помощники: _dispatch_service, _extract_hresult, _classify_hr
- синтаксические анализаторы: parse_triggers, parse_actions

Совместимость
-------------
Python 3.11+.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

import pywintypes  # type: ignore[import-not-found]
import pythoncom  # type: ignore[import-not-found]
import win32com.client as win32  # type: ignore[import-not-found]

from SRC.SETUP.setup_utils import _dispatch_service, _extract_hresult, _classify_hr
from SRC.SETUP.parsers import parse_actions, parse_triggers  # type: ignore[import-not-found]

# Сводный кортеж COM‑исключений для единообразной аннотации типов и отладки.
_COM_ERRORS = (pywintypes.com_error, pythoncom.com_error)  # type: ignore[name-defined]


# =========================
# МОДЕЛЬ ДАННЫХ РЕЗУЛЬТАТА
# =========================
@dataclass(frozen=True, slots=True)
class TaskInfo:
    """DTO‑структура с данными зарегистрированной задачи планировщика.

    Поля подобраны под частые вопросы: имя/путь, включена ли задача, автор и
    описание, триггеры и действия, уровень прав и флаг скрытия задачи.
    """

    name: str
    path: str
    enabled: bool
    description: str
    author: str
    triggers: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    run_as_admin: bool
    hidden: bool

    @staticmethod
    def from_task(task: Any) -> TaskInfo:
        """Преобразовать COM‑объект IRegisteredTask в :class:`TaskInfo`.

        Args:
            task: COM‑объект зарегистрированной задачи (IRegisteredTask).
        Returns:
            Экземпляр :class:`TaskInfo` с устойчивыми к отсутствию полей значениями.
        """
        # Достаём под‑объекты определения задачи; берём только то, что нужно.
        d = getattr(task, "Definition", None)
        reg = getattr(d, "RegistrationInfo", None) if d else None
        principal = getattr(d, "Principal", None) if d else None
        settings = getattr(d, "Settings", None) if d else None

        return TaskInfo(
            name=getattr(task, "Name", ""),
            path=getattr(task, "Path", ""),
            enabled=bool(getattr(task, "Enabled", True)),
            description=getattr(reg, "Description", "") if reg else "",
            author=getattr(reg, "Author", "") if reg else "",
            # Парсинг делегируем специализированным функциям.
            triggers=(parse_triggers(d) if d else []),
            actions=parse_actions(d) if d else [],
            run_as_admin=(
                (getattr(principal, "RunLevel", 0) == 1) if principal else False
            ),
            hidden=bool(getattr(settings, "Hidden", False)) if settings else False,
        )

    def to_dict(self) -> dict[str, Any]:
        """Сериализация в обычный ``dict`` для JSON/логов/отладки."""
        return asdict(self)


# =========================
# ОСНОВНОЙ КЛАСС ОБОЛОЧКИ
# =========================
class Scheduler:
    """Обёртка над Windows Task Scheduler COM API.

    Публичный интерфейс:
      - `connect`
      - `get_task_info`
      - `create_weekly_exec_task`
      - `update_weekly_exec_task`
      - `delete_task`

    Ограничение: создаваемая задача состоит из одного Exec‑действия и одного
    Weekly‑триггера. Это покрывает распространённый сценарий «запусти X каждую
    неделю в выбранные дни» и оставляет API компактным.
    """

    # Константы COM API Планировщика
    TASK_TRIGGER_WEEKLY = 3
    TASK_ACTION_EXEC = 0
    TASK_LOGON_INTERACTIVE_TOKEN = 3

    TASK_CREATE = 2
    TASK_UPDATE = 4
    TASK_CREATE_OR_UPDATE = TASK_CREATE | TASK_UPDATE

    RUNLEVEL_HIGHEST = 1
    RUNLEVEL_LEAST = 0

    def __init__(self) -> None:
        # Дескриптор (ссылка на) COM‑службы Schedule.Service. Инициализируется в connect().
        self._svc: Any | None = None

    # ——— Соединение с COM‑службой ———
    def connect(self) -> None:
        """Подключиться к службе планировщика.

        Raises:
            RuntimeError: если COM‑служба недоступна или Connect() завершился с ошибкой.
        """
        self._svc = _dispatch_service()
        try:
            self._svc.Connect()
        except pywintypes.com_error as ex:  # type: ignore[name-defined]
            hr = _extract_hresult(ex)
            raise RuntimeError(
                f"Нет подключения к службе планировщика, HRESULT={hr}"
            ) from None

    def _svc_or_connect(self) -> Any:
        """Гарантировать наличие COM‑службы: вернуть существующую или подключиться."""
        if self._svc is None:
            self.connect()
        return self._svc

    # ——— Доступ к объектам планировщика ———
    def _get_folder(self, folder_path: str, *, create: bool = False) -> Any | None:
        """Получить папку планировщика по пути.

        Args:
            folder_path: Путь к папке (например, "\\" или "\\MyFolder").
            create: Создать папку в корне при отсутствии.
        Returns:
            COM‑объект ITaskFolder либо ``None``, если не найдено и ``create=False``.
        Raises:
            PermissionError: если нет прав на чтение/создание папки.
            Иные COM‑ошибки пробрасываются наверх.
        """
        svc = self._svc_or_connect()
        try:
            return svc.GetFolder(folder_path)
        except pywintypes.com_error as ex:  # type: ignore[name-defined]
            kind = _classify_hr(_extract_hresult(ex))
            if kind == "not_found":
                if create:
                    parent = svc.GetFolder("\\")
                    return parent.CreateFolder(folder_path)
                return None
            if kind == "denied":
                raise PermissionError("Нет доступа к папке планировщика") from ex
            raise

    def _get_task(self, folder: Any, name: str) -> Any | None:
        """Получить зарегистрированную задачу по имени внутри папки.

        Returns:
            COM‑объект IRegisteredTask либо ``None``, если задача отсутствует.
        Raises:
            PermissionError: если нет прав на доступ к задаче.
        """
        try:
            return folder.GetTask(name)
        except pywintypes.com_error as ex:  # type: ignore[name-defined]
            kind = _classify_hr(_extract_hresult(ex))
            if kind == "not_found":
                return None
            if kind == "denied":
                raise PermissionError("Нет доступа к задаче планировщика") from ex
            raise

    # ——— Чтение данных ———
    def get_task_info(self, folder_path: str, name: str) -> dict[str, Any] | None:
        """Прочитать сведения о задаче и вернуть их как словарь.

        Args:
            folder_path: Путь к папке планировщика.
            name: Имя задачи.
        Returns:
            Словарь с полями: class:`TaskInfo` или ``None``, если папка/задача отсутствуют.
        """
        folder = self._get_folder(folder_path, create=False)
        if folder is None:
            return None

        task = self._get_task(folder, name)
        if task is None:
            return None

        return TaskInfo.from_task(task).to_dict()

    # ——— Помощники для создания Weekly Exec‑задачи ———

    def _build_taskdef(
        self, *, hidden: bool, run_as_admin: bool, description: str
    ) -> Any:
        """Инициализировать пустой TaskDefinition с базовыми настройками.

        Параметры подобраны под типичный сценарий интерактивного запуска.
        """
        svc = self._svc_or_connect()
        td = svc.NewTask(0)
        # Регистрация/описание
        td.RegistrationInfo.Description = description
        # Настройки выполнения
        td.Settings.Hidden = hidden
        td.Settings.Enabled = True
        td.Settings.StartWhenAvailable = False
        td.Settings.StopIfGoingOnBatteries = False
        td.Settings.WakeToRun = True
        td.Settings.DisallowStartIfOnBatteries = False
        # учётная запись пользователя/уровень прав
        td.Principal.LogonType = self.TASK_LOGON_INTERACTIVE_TOKEN
        td.Principal.RunLevel = (
            self.RUNLEVEL_HIGHEST if run_as_admin else self.RUNLEVEL_LEAST
        )
        return td

    def _add_weekly_trigger(
        self, td: Any, *, start_iso: str, weeks_interval: int, days_of_week: int
    ) -> None:
        """Добавить weekly‑триггер с ISO‑времени старта и маской дней недели."""
        trg = td.Triggers.Create(self.TASK_TRIGGER_WEEKLY)
        w = win32.CastTo(trg, "IWeeklyTrigger")
        w.WeeksInterval = max(1, int(weeks_interval))
        w.DaysOfWeek = int(days_of_week)
        w.StartBoundary = start_iso

    def _add_exec_action(
        self, td: Any, *, program: str, arguments: str, working_dir: str
    ) -> None:
        """Добавить единственное Exec‑действие с путём, аргументами и рабочей директорией."""
        act = td.Actions.Create(self.TASK_ACTION_EXEC)
        ea = win32.CastTo(act, "IExecAction")
        ea.Path = program
        ea.Arguments = arguments or ""
        ea.WorkingDirectory = working_dir or ""

    # ——— Создание Weekly Exec‑задачи ———
    def create_weekly_exec_task(
        self,
        folder_path: str,
        name: str,
        program: str,
        start_iso: str,
        *,
        author: str = "",
        arguments: str = "",
        working_dir: str = "",
        description: str = "",
        weeks_interval: int = 1,
        days_of_week: int = 127,
        hidden: bool = True,
        run_as_admin: bool = True,
        overwrite: bool = False,
    ) -> None:
        """Создать (или обновить) задачу: одно Exec‑действие + один Weekly‑триггер.

        Args:
            folder_path: Путь к папке.
            name: Имя задачи.
            program: Исполняемый файл.
            start_iso: Время старта в ISO‑формате (например, "2025-10-06T09:00:00").
            author: Имя автора (опционально).
            arguments: Аргументы запуска.
            working_dir: Рабочая директория.
            description: Описание задачи.
            weeks_interval: Интервал недель (>=1).
            days_of_week: Маска дней недели (по API планировщика).
            hidden: Скрывать задачу в UI.
            run_as_admin: Запуск с повышенными правами.
            overwrite: Разрешить перезапись существующей задачи.

        Raises:
            PermissionError: нет прав на регистрацию задачи.
            FileNotFoundError: не удалось создать/получить папку.
            RuntimeError: иные COM‑ошибки с включённым HRESULT.
        """
        folder = self._get_folder(folder_path, create=True)
        if folder is None:
            raise FileNotFoundError(
                f"Не удалось создать или получить папку '{folder_path}'"
            )

        td = self._build_taskdef(
            hidden=hidden, run_as_admin=run_as_admin, description=description
        )
        self._add_weekly_trigger(
            td,
            start_iso=start_iso,
            weeks_interval=weeks_interval,
            days_of_week=days_of_week,
        )
        self._add_exec_action(
            td, program=program, arguments=arguments, working_dir=working_dir
        )

        flags = self.TASK_CREATE_OR_UPDATE if overwrite else self.TASK_CREATE
        try:
            folder.RegisterTaskDefinition(
                name, td, flags, "", "", self.TASK_LOGON_INTERACTIVE_TOKEN, ""
            )
        except pywintypes.com_error as ex:  # type: ignore[name-defined]
            kind = _classify_hr(_extract_hresult(ex))
            if kind == "denied":
                raise PermissionError("Нет прав для регистрации задачи") from ex
            hr = _extract_hresult(ex)
            raise RuntimeError(f"Ошибка регистрации задачи, HRESULT={hr}") from ex

    # ——— Обязательные геттеры/проверки ———
    def _require_folder(self, folder_path: str) -> Any:
        """Вернуть ITaskFolder или выбросить FileNotFoundError."""
        folder = self._get_folder(folder_path, create=False)
        if folder is None:
            raise FileNotFoundError(f"Папка планировщика '{folder_path}' не найдена")
        return folder

    def _require_task(self, folder: Any, name: str) -> Any:
        """Вернуть IRegisteredTask или выбросить FileNotFoundError."""
        task = self._get_task(folder, name)
        if task is None:
            raise FileNotFoundError(f"Задача '{name}' не найдена")
        return task

    def _require_definition(self, task: Any) -> Any:
        """Вернуть ITaskDefinition или выбросить RuntimeError при отсутствии."""
        d = getattr(task, "Definition", None)
        if d is None:
            raise RuntimeError("У задачи нет Definition")
        return d

    def _get_weekly_trigger(self, d: Any) -> Any:
        """Найти weekly‑триггер в TaskDefinition или выбросить RuntimeError."""
        for trg in d.Triggers:
            if int(getattr(trg, "Type", -1)) == self.TASK_TRIGGER_WEEKLY:
                return trg
        raise RuntimeError("У задачи нет weekly‑триггера")

    # ——— Обновление ———
    def _apply_updates(
        self,
        d: Any,
        *,
        description: str | None,
        days_of_week: int | None,
        start_iso: str | None,
    ) -> None:
        """Применить изменения к TaskDefinition: описание и weekly‑триггер."""
        # Описание
        if description is not None:
            reg = getattr(d, "RegistrationInfo", None)
            if reg is None:
                raise RuntimeError("Нет RegistrationInfo у Definition")
            reg.Description = description

        # Weekly‑триггер
        if days_of_week is not None or start_iso is not None:
            w = win32.CastTo(self._get_weekly_trigger(d), "IWeeklyTrigger")
            if days_of_week is not None:
                w.DaysOfWeek = int(days_of_week)
            if start_iso is not None:
                w.StartBoundary = start_iso

    def _register_update(self, folder: Any, name: str, d: Any) -> None:
        """Перерегистрировать задачу с флагом UPDATE и корректной авторизацией."""
        try:
            folder.RegisterTaskDefinition(
                name,
                d,
                self.TASK_UPDATE,
                "",  # пользователь
                "",  # пароль
                self.TASK_LOGON_INTERACTIVE_TOKEN,
                "",
            )
        except pywintypes.com_error as ex:  # type: ignore[name-defined]
            kind = _classify_hr(_extract_hresult(ex))
            if kind == "denied":
                raise PermissionError("Нет прав для обновления задачи") from ex
            hr = _extract_hresult(ex)
            raise RuntimeError(f"Ошибка обновления задачи, HRESULT={hr}") from ex

    def update_weekly_exec_task(
        self,
        folder_path: str,
        name: str,
        *,
        description: str | None = None,
        days_of_week: int | None = None,
        start_iso: str | None = None,
    ) -> None:
        """Обновить существующую weekly‑задачу: описание, дни, время запуска.

        Raises:
            FileNotFoundError: папка или задача не найдены.
            PermissionError: нет прав для обновления.
            RuntimeError: отсутствие weekly‑триггера или иные COM‑ошибки.
        """
        folder = self._require_folder(folder_path)
        task = self._require_task(folder, name)
        d = self._require_definition(task)

        self._apply_updates(
            d, description=description, days_of_week=days_of_week, start_iso=start_iso
        )
        self._register_update(folder, name, d)

    # ——— Удаление ———
    def delete_task(self, folder_path: str, name: str) -> None:
        """Удалить задачу из указанной папки.

        Raises:
            FileNotFoundError: если папка или задача не найдены.
            PermissionError: если нет прав на удаление.
            RuntimeError: прочие COM‑ошибки с HRESULT.
        """
        folder = self._get_folder(folder_path, create=False)
        if folder is None:
            raise FileNotFoundError(f"Папка '{folder_path}' не найдена")

        task = self._get_task(folder, name)
        if task is None:
            raise FileNotFoundError(f"Задача '{name}' не найдена")

        try:
            folder.DeleteTask(name, 0)
        except pywintypes.com_error as ex:  # type: ignore[name-defined]
            kind = _classify_hr(_extract_hresult(ex))
            if kind == "denied":
                raise PermissionError("Нет прав на удаление задачи") from ex
            hr = _extract_hresult(ex)
            raise RuntimeError(f"Ошибка удаления задачи, HRESULT={hr}") from ex


# =========================
# ПРИМЕР ИСПОЛЬЗОВАНИЯ (ручной прогон)
# =========================
if __name__ == "__main__":

    def _print_info(sch: Scheduler, folder_path: str, task_name: str) -> None:
        """Сервисная печать сведений о задаче для ручной проверки."""
        info = sch.get_task_info(folder_path, task_name)
        if info is None:
            print(f"    Задача '{task_name}' не найдена")
        else:
            for k, v in info.items():
                print(f"    {k}: {v}")

    folder_path_ = "\\MyFolder"
    task_name_ = "save_weekly"

    sch_ = Scheduler()
    sch_.connect()

    try:
        print("\n--> Создание задачи\n")
        sch_.create_weekly_exec_task(
            folder_path_,
            task_name_,
            program=r"C:\\Windows\\System32\\notepad.exe",
            start_iso="2025-10-06T09:00:00",
            author="Bolshakov",
            working_dir="",
            description="Демо-задача: еженедельный запуск Блокнота в понедельник",
            weeks_interval=1,
            overwrite=True,
        )
    except Exception as e:
        print(f"    Ошибка при создании задачи: {e}")

    _print_info(sch_, folder_path_, task_name_)

    print("\n--> Обновление задачи\n")
    sch_.update_weekly_exec_task(
        folder_path_,
        task_name_,
        description="Новое описание",
        days_of_week=0b0000010,  # только понедельник = 2
        start_iso="2025-10-06T09:30:00",
    )
    _print_info(sch_, folder_path_, task_name_)

    print("\n--> Удаление задачи\n")
    sch_.delete_task(folder_path_, task_name_)
    _print_info(sch_, folder_path_, task_name_)
