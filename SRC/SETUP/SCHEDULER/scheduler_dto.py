from dataclasses import dataclass


# fmt: off
@dataclass
class TaskConfig:
    """
    Конфигурация задачи планировщика, собранная из UI или задачи планировщика.

    Атрибуты:
        task_path               : Полный путь к задаче в планировщике (\\Folder\\TaskName).
        mask_days               : 7-битная маска дней недели (bit0=Пн .. bit6=Вс).
        start_time              : Время запуска исполняемого файла в формате "HH:MM".
        executable_path         : Путь к исполняемому файлу.
        work_directory_path     : Путь к рабочей директории
        description             : Описание задачи (отображается в планировщике).
    """
    task_path                   : str
    mask_days                   : int
    start_time                  : str
    executable_path             : str
    work_directory_path         : str
    description                 : str
# fmt: on
