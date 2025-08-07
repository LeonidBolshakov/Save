from SRC.GENERAL.constants import Constants as C


class TextMessage(frozenset):
    arch_exists = (
        "Существует {obj_type} {archive_path}, имя которого, совпадает с именем архива. "
        "Архивация невозможна."
    )
    archive_name_generation = "Генерация имени архива"
    archiver_not_found = (
        f"На компьютере не найдена программа {C.PATTERN_PROGRAMME}. Надо установить"
    )
    canceled_by_user = "Процесс прерван пользователем"
    critical_error_type = "Ошибка типа {type}: {e}"
    empty = "Пусто"
    env_not_found = "Файл {env} не найден. Текущая директория {dir_archive}"
    error_address_email = "Ошибка в email адресе: {e}"
    error_compose_message = "Ошибка при составлении e-mail сообщения {e}"
    error_in_compression_level = (
        "Уровень компрессии ({level}) должен быть целым число от 0 до 9 включительно"
    )
    error_list_files = (
        "Ошибка проверки существования директории с архивами в облаке: {e}"
    )
    error_load_config = (
        "Ошибка загрузки конфигурационного файла {config_file_path}: {e}"
    )
    error_local_archive = "Ошибка при создании локального архива {e}"
    error_run_programme = (
        "[Поиск программы]. Вариант программы по адресу {path} вернул ошибку {e}"
    )
    error_run_programme_except = (
        "[Поиск программы]. Вариант программы по адресу {path} выдал ошибку {e}"
    )
    error_run_system_path = (
        "[Поиск программы]. Выполнение программы по системным path закончилось неудачей"
    )
    error_saving_config = "Ошибка сохранения в конфиг файл: {e}"
    error_saving_env = "Ошибка сохранения {var_name}: {e}"
    error_send_email = "Ошибка отправки email: {e}"
    error_starting_archiving = "Ошибка при запуске процесса архивации: {e}"
    exists_list_file = "Файл списка файлов архивации существует: {list_file_path}"
    failed_send_email = "Все попытки отправки email провалились"
    fatal_error = "Архивация завершена с ФАТАЛЬНЫМИ ошибками"
    file_exists = "Файл {remote_path} уже существует на Яндекс-Диске"
    file_numbers_found = "Найдены номера файлов: {file_nums}"
    format_log = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    getting_file_numbers = "Получение номеров файлов из {archive}"
    init_arch = "Инициализация CreateArch7zSpec"
    init_FileArchiving = "Инициализация FileArchiving"
    init_main = "Начало процесса архивации и сохранения файлов в облако"
    init_yadisk = "Инициализация YandexDisk"
    invalid_file_extension = (
        "Недопустимое расширение файла архива: {suffix} - "
        "должно быть {archive_suffix}"
    )
    invalid_path_programme = f"Некорректный путь к архиватору в конфиге: " + "{path}"
    missing_email_credentials = "отсутствуют учетные данные email"
    missing_mandatory_variables = (
        "Отсутствуют обязательные переменные окружения:\n"
        "{missing}.\n"
        "Переменные Задаются в файле {dot_env} или в Windows Credential Manager (Диспетчер учётных данных)."
    )
    path_to_cloud = "Путь на архив в облаке: {remote_path}"
    none_element = "Обнаружен None-элемент в списке файлов облачного диска"
    no_fatal_error = "Архивация завершена с НЕ фатальными ошибками"
    no_path_local = "Не задан путь на архив, в который собираются сохраняемые файлы"
    not_key_in_config = f"В конфиге нет ключа {C.CONFIG_KEY_SEVEN_ZIP_PATH}"
    not_enough_rights = "Недостаточно прав для записи в {remote_path}"
    not_found_config_file = "Конфигурационный файл ({config_file_path}) с путём на программу не задан или не существует - "
    not_found_list_file_path = (
        "Не найден файл, состоящий из списка архивируемых файлов - {list_file_path}"
    )
    not_save_env = (
        "{var_name} не сохранён в keyring! Записываемое значение не равно прочитанному."
    )
    not_save_env_empty = "{var_name} не сохранён в keyring! Задано пустое значение."
    path_local_archive = "Путь к архиву на локальном диске: {local_path_str}"
    permission_error = "[Поиск программы]. Нет доступа к {path}"
    program_is_localed = "Программа находится по пути {path}"
    prompt = "{var} = {current}, введите новое или Enter, чтобы оставить прежнее:"
    search_all_disks = "Поиск программы по всем дискам..."
    search_in_config = (
        "[Поиск программы]. Поиск программы по пути, указанном в файле конфигураторе"
    )
    search_in_standard_paths = (
        "[Поиск программы]. Поиск {programme_template} в стандартных путях"
    )
    search_in_standard_paths_failed = "Поиск в стандартных путях неудачен"
    start_create_archive = "Начало создания архива"
    start_load_file = "Начало загрузки файла {local_path}"
    start_main = "Запуск процесса резервного копирования"
    start_send_email = "Отправка email: {subject}"
    starting_archiving = "Запуск архивации: {cmd}"
    successful_archiving = "Архивация завершена успешно"
    successful_send_email = "Служебное сообщение отправлено по e-mail"
    task_error = (
        "{name_max_level} --> Задание завершено с ошибками уровня {name_max_level}."
    )
    task_successfully = "{name_max_level} --> Задание по формированию и сохранению архива успешно завершено!"
    task_warnings = (
        "{name_max_level} --> Задание завершено с предупреждением/предупреждениями."
    )
    time_run = "Время выполнения: {time} сек"
    unregistered_program = (
        "Задана незарегистрированная программа записи на облачный диск.\n"
        "Параметр ENV '{env}'"
    )
