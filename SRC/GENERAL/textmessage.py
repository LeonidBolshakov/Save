from SRC.GENERAL.constants import Constants as C


class TextMessage(frozenset):
    arch_exists = (
        "Существует {obj_type} {archive_path}, имя которого, совпадает с именем архива. "
        "Архивация невозможна."
    )
    archive_name_generation = "Генерация имени удалённого архива"
    archiver_not_found = (
        f"На компьютере не найдена программа {C.FULL_NAME_SEVEN_Z}. Надо установить"
    )
    canceled_by_user = "Процесс прерван пользователем"
    env_not_found = "Файл {env} не найден. Текущая директория {dir_archive}"
    error_address_email = "Ошибка в email адресе: {e}"
    error_compose_message = "Ошибка при составлении e-mail сообщения {e}"
    error_in_compression_level = (
        "Уровень компрессии ({level}) должен быть целым число от 0 до 9 включительно"
    )
    error_load_config = (
        "Ошибка загрузки конфигурационного файла, содержащего полный путь к архиватору."
        "\n{config_file_path}: {e}"
    )
    error_run_programme = (
        "[Поиск программы]. Вариант программы по адресу {path} вернул ошибку {e}"
    )
    error_run_system_path = (
        "[Поиск программы]. Выполнение программы по системным PATH закончилось неудачей"
    )
    error_saving_config = (
        "Ошибка сохранения в конфигурационный файл,"
        "\nсодержащий полный путь на исполняемую программу:"
        "\n{e}"
    )
    error_saving_env = (
        "Ошибка сохранения в хранилище паролей. Переменная - {var_name}: {e}"
    )
    error_send_email = "Ошибка отправки email: {e}"
    error_starting_archiving = "Ошибка при запуске процесса архивации: {e}"
    exists_list_file = "Файл списка файлов архивации существует: {list_file_path}"
    failed_send_email = "Все попытки отправки email провалились"
    file_numbers_found = "Найдены номера файлов: {file_nums}"
    getting_file_numbers = "Получение номеров файлов из {archive}"
    init_arch = "Начало архивации"
    init_SearchProgramme = "Поиск архиватора"
    init_main = "Начало работы программы"
    invalid_path_programme = (
        "В конфигураторе {path} указан путь к некорректному архиватору."
    )
    missing_email_credentials = "отсутствуют учетные данные email отправителя"
    missing_mandatory_variables = (
        "Отсутствуют обязательные переменные окружения:\n"
        "{missing}.\n"
        "Переменные Задаются в файле {dot_env} или в\n"
        "Windows Credential Manager (Диспетчер учётных данных)."
    )
    path_to_cloud = "Путь на архив в облаке: {remote_path}"
    none_element = "Обнаружен None-элемент в списке файлов облачного диска"
    not_key_in_config = (
        "В файле конфигураторе не задана информация о пути архиватора: {key}"
    )
    not_found_config_file = "Конфигурационный файл ({config_file_path}) с путём на программу не задан или не существует - "
    not_found_list_file_path = (
        "Не найден файл, состоящий из списка архивируемых файлов - {list_file_path}"
    )
    not_save_env = "{var_name} не сохранён в keyring! Записываемое значение {value} не равно прочитанному {result}."
    not_save_env_empty = "{var_name} не сохранён в keyring! Задано пустое значение."
    password_not_set = "Пароль на архив не задан"
    permission_error = "[Поиск программы]. Нет доступа к {path} -> {item}"
    program_in_system_path = (
        "Программа находится в системных путях. Путь к ней  можно не указывать"
    )
    program_is_localed = "Программа находится по пути {path}"
    prompt = "{var} = {current}, введите новое или Enter, чтобы оставить прежнее:"
    search_all_disks = "[Поиск программы]. Поиск программы по всем дискам..."
    search_in_config = (
        "[Поиск программы]. Поиск программы по пути, указанном в файле конфигураторе"
    )
    search_in_standard_paths = (
        "[Поиск программы]. Поиск {programme_full_name} в стандартных путях"
    )
    search_in_standard_paths_failed = "Поиск в стандартных путях неудачен"
    start_send_email = "Отправка email: {subject}"
    starting_archiving = "Запуск архивации: {cmd}"
    task_error = (
        "{max_level_name} --> Задание завершено с ошибками уровня {name_max_level}."
    )
    task_successfully = "{max_level_name} --> Задание по формированию и сохранению архива успешно завершено!"
    task_warnings = (
        "{max_level_name} --> Задание завершено с предупреждением/предупреждениями."
    )
    time_run = "Время выполнения: {time} сек"
    unregistered_program = (
        "Задан непредусмотренный программой облачный диск.\n" "Параметр ENV '{env}'"
    )
