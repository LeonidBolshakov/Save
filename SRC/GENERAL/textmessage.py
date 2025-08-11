from SRC.GENERAL.constants import Constants as C


class TextMessage(frozenset):
    arch_exists = (
        "На локальном диске существует {obj_type} {archive_path}, имя которого, совпадает с именем архива. "
        "Архивация невозможна."
    )
    archive_name_generation = "Генерация имени удалённого архива"
    archiver_not_found = (
        f"На компьютере не найдена программа {C.FULL_NAME_SEVEN_Z}. Надо установить"
    )
    canceled_by_user = "Процесс прерван пользователем"
    empty = "[Пусто]"
    entropy_brute_force = "уязвим к перебору"
    entropy_highly = "высоко-стойкий"
    entropy_Unreliable = "ненадёжный (взламывается мгновенно)"
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
    error_subprocess = "Ошибка при выполнении процесса {cmd_mask}. Код возврата {return_code}.\n{stderr}"
    error_unknown = "Неизвестная ошибка"
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
    missing_mandatory_variables = "Отсутствуют обязательные переменные окружения"
    missing_mandatory_variables_env = (
        "Отсутствуют обязательные переменные окружения:\n"
        "{missing}.\n"
        "Включите переменные и их значения в файл {dot_env}"
    )
    missing_mandatory_variables_keyring = (
        "Отсутствуют обязательные переменные окружения:\n"
        "{missing}.\n"
        + f"Задайте переменный с помощью программы {C.PROGRAM_WRITE_VARS}"
    )
    password_message = (
        "Пароль архива имеет силу - {strength_str}, сложность вскрытия {entropy_str}.\n"
        "Пароль задают программой {program}, параметр {parameter}"
    )
    path_to_cloud = "Путь на архив в облаке: {remote_path}"
    none_element = "Обнаружен None-элемент в списке файлов облачного диска"
    not_key_in_config = (
        "В файле конфигураторе не задана информация о пути архиватора: {key}"
    )
    not_found_config_file = "Конфигурационный файл ({config_file_path}) с путём на программу не задан или не существует - "
    not_found_list_file_path = (
        "Не найден файл, состоящий из списка архивируемых файлов.\n"
        "Должен быть расположен по пути - {list_file_path}\n"
        "Этот путь задаётся в файле {env} параметром {parameter}\n"
        "Если параметр в файле не задан, то, по умолчанию, он равен {default}"
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
    strength_very_weak = "очень слабый"
    strength_weak = "слабый"
    strength_medium = "средний"
    strength_strong = "надёжный"
    task_error = (
        "{max_level_name} --> Задание завершено с ошибками уровня {max_level_name}."
    )
    task_successfully = "{max_level_name} --> Задание по формированию и сохранению архива успешно завершено!"
    task_warnings = (
        "{max_level_name} --> Задание завершено с предупреждением/предупреждениями."
    )
    time_run = "Время выполнения: {time} сек"
    unintended_log_level = (
        "Программы анализа пароля выдали непредусмотренный уровень лога - {level}"
    )
    unregistered_program = (
        "Задан непредусмотренный программой облачный диск.\n" "Параметр ENV '{env}'"
    )
