import win32com.client
import datetime


def create_task():
    scheduler = win32com.client.Dispatch("Schedule.Service")
    scheduler.Connect()

    # Получаем корневую папку
    root_folder = scheduler.GetFolder("\\")

    # Создаём определение задачи
    task_def = scheduler.NewTask(0)  # 0 = Task Scheduler 2.0

    # Настраиваем триггер (например, ежедневный запуск)
    trigger = task_def.Triggers.Create(2)  # 2 = DailyTrigger
    trigger.StartBoundary = (
        datetime.datetime.now().replace(hour=14, minute=0, second=0).isoformat() + "Z"
    )  # ISO + 'Z' (UTC)
    trigger.DaysInterval = 1

    # Настраиваем действие (запуск Python-скрипта)
    action = task_def.Actions.Create(0)  # 0 = Executable action
    action.Path = r"C:\Python39\python.exe"  # Полный путь к python.exe
    action.Arguments = r"C:\path\to\your_script.py"  # Полный путь к скрипту

    # Настройки задачи
    task_def.RegistrationInfo.Description = "Моя задача Python"
    task_def.Settings.Enabled = True
    task_def.Settings.StartWhenAvailable = True
    task_def.Principal.RunLevel = 1  # 1 = TASK_RUNLEVEL_HIGHEST (админ)

    try:
        # Регистрируем задачу (LOGON_PASSWORD для текущего пользователя)
        root_folder.RegisterTaskDefinition(
            "Название задачи",  # Имя задачи (без пути)
            task_def,
            6,  # 6 = CREATE_OR_UPDATE
            "",  # Пользователь (пусто = текущий)
            "",  # Пароль (пусто, если LOGON_INTERACTIVE)
            3,  # 3 = TASK_LOGON_INTERACTIVE_TOKEN (лучше, чем 1)
        )
        print("✅ Задача успешно создана!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


create_task()
