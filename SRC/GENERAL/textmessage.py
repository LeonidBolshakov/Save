from SRC.GENERAL.constant import Constant as C


class TextMessage(frozenset):
    arch_exists = (
        "Существует {obj_type} {arch_path}, имя которого, совпадает с именем архива. "
        "Архивация невозможна."
    )
    archive_name_generation = "Генерация имени архива"
    authorization_error = "Ошибка авторизации {e}"
    authorization_timeout = "Превышено время ожидания авторизации {e}"
    callback_timeout = "Таймаут ожидания callback"
    canceled_authorization = "Отмена авторизации пользователем"
    canceled_by_user = "Процесс прерван пользователем"
    critical_error = "Критическая ошибка: {e}"
    critical_error_type = "Ошибка типа {type}: {e}"
    dangerous_symbols = "Redirect URI содержит опасные символы"
    dictionary_expected = "Ожидался словарь, получен {type}.\nОтвет: {response}..."
    during = "Файл загружен за {during} сек."
    empty = "Пусто"
    env_not_found = "Файл {env} не найден. Текущая директория {dir}"
    error_address_email = "Ошибка в email адресе: {e}"
    error_API_Yandex_disk = "API Яндекс.Диска не вернуло путь к файлу"
    error_check_token = "Ошибка проверки токена доступа через API: {e}"
    error_list_files = "Ошибка получения списка файлов: {e}"
    error_load_7z = (
        f"Ошибка загрузки конфигурационного файла с путём на {C.PATTERN_7_Z}"
        + "{config_file}: {e}"
    )
    error_load_file = "Ошибка при загрузке файла: {err}"
    error_load_tokens = (
        "[Token Load] Ошибка загрузки закрытой информации из keyring: {e}"
    )
    error_local_archive = "Ошибка при создании локального архива {e}"
    error_processing_request = "Ошибка обработки запроса авторизации Яндекс: {e}"
    error_refresh_token = "Ошибка {status_code} при обновлении токена доступа с помощью refresh токена- {e}"
    error_run_7z = (
        "[Поиск программы 7z]. Вариант программы по адресу {path} вернул ошибку {e}"
    )
    error_run_7z_except = "[Поиск программы 7z]. Вариант программы по адресу {path} выдал грубую ошибку {e}"
    error_saving_config = "Ошибка сохранения в конфиг файл: {e}"
    error_saving_env = "Ошибка сохранения {var_name}: {e}"
    error_saving_tokens = "Ошибка сохранения закрытой информации в keyring: {e}"
    error_send_email = "Ошибка отправки email: {e}"
    error_starting_archiving = "Ошибка при запуске процесса архивации: {e}"
    error_upload_URL = (
        "Ошибка получения upload URL для быстрой загрузки на Яндекс-Диск: {text}"
    )
    exists_list_file = "Файл списка файлов архивации существует: {list_file_path}"
    expires_in = "В токен доступа, полученном с сервера время жизни токена равно {expires_in} сек."
    expires_in_error = "В токен доступа, полученном с сервера время жизни токена не плавающее число {key}"
    failed_access_token = "Не удалось получить токен доступа"
    failed_send_email = "Все попытки отправки email провалились"
    fast_load = "Быстрая загрузка файла {local_path}"
    fatal_error = "Архивация завершена с ФАТАЛЬНЫМИ ошибками"
    file_exists = "Файл {remote_path} уже существует на Яндекс-Диске"
    file_numbers_found = "Найдены номера файлов: {file_nums}"
    folder_created = "Папка {archive_path} создана"
    folder_not_found = "Папка {archive_path} не найдена, создаем"
    format_log = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    get_token = "Получение токена авторизации"
    get_token_error = "Ошибка получения токена авторизации: {e}"
    getting_file_numbers = "Получение номеров файлов из {archive}"
    init_arch = "Инициализация Arch7zSpec"
    init_FileArchiving = "Инициализация FileArchiving"
    init_load_to_disk = "Инициализация загрузки файла на Яндекс.Диск"
    init_main = "Начало процесса архивации и сохранения файлов в облако"
    init_yadisk = "Инициализация YandexDisk"
    invalid_file_extension = (
        "Недопустимое расширение файла архива: {suffix} - "
        "должно быть {archive_suffix}"
    )
    invalid_path_7z = f"Некорректный путь к {C.PATTERN_7_Z} в конфиге:" + "{path}"
    invalid_port = (
        "В переменных окружения не задан, или задан как не целое число, номер порта, заданный в приложении Яндекс "
        + f"{C.ENV_YANDEX_PORT}"
        + "{e}"
    )
    invalid_token = "Недействительный токен доступа к Яндекс.Диск!"
    load = "Загрузка {local_path} -> {remote_path}"
    load_success = "Файл {local_path} успешно загружен в {remote_path}"
    loaded_token = "Успешно загружены сохраненные закрытые данные"
    missing_email_credentials = "отсутствуют учетные данные email"
    missing_mandatory_variables = (
        "❌ Отсутствуют обязательные переменные окружения./n"
        "Задаются в файле {dot_env} или в keyring:/n{missing)}"
    )
    no_auth_code = "Не удалось извлечь код авторизации"
    no_callback_path = "Callback path не установлен"
    no_correct_redirect_uri = (
        "Некорректный redirect_uri: {redirect_uri}./n"
        "Должен соответствовать зарегистрированному в "
        "кабинете разработчика Яндекса"
    )
    no_expires_in = (
        "expires_in (время жизни токена) нет в токен полученном с сервера.\n"
        "Полагается, что время жизни не ограничено."
    )
    no_fatal_error = "Архивация завершена с НЕ фатальными ошибками"
    no_path_local = "Не задан путь на архив, в который собираются сохраняемые файлы"
    no_refresh_token = (
        "Refresh token отсутствует/n"
        "Восстановление токена доступа с помощью refresh токена отменено."
    )
    no_token_in_response = (
        "Токен доступа не получен в ответе сервера\n"
        "Недействительный токен или ошибка в Internet"
    )
    no_valid_token = "Токен недействителен. Нет доступа к Яндекс-Диск."
    none_element = "Обнаружен None-элемент в списке файлов Яндекс-Диска."
    not_key_in_config = f"В конфиге нет ключа {C.CONFIG_KEY_SEVEN_ZIP_PATH}"
    not_enough_rights = "Недостаточно прав для записи в {remote_path}"
    not_found_7z = f"На компьютере не найден архиватор {C.PATTERN_7_Z}. Надо установить"
    not_float = "[Token Load] Время истечения токена не число с плавающей запятой: {e}"
    not_found_config_file = (
        f"Конфигурационный файл с путём на программу {C.PATTERN_7_Z} не задан или не существует"
        + "{config_file}"
    )
    not_found_list_file_path = (
        "Не найден файл, состоящий из списка архивируемых файлов - " "{list_file_path}"
    )
    not_safe_uri = "Получен небезопасный callback URI: {callback_path}"
    not_save_env = "❌ {var_name} не сохранён в keyring! Записываемое значение не равно прочитанному."
    not_save_env_empty = "❌ {var_name} не сохранён в keyring! Задано пустое значение."
    not_valid_json = "Невалидный JSON: {e}. Ответ: {response}"
    path_local_archive = "Путь к архиву на локальном диске: {local_path_str}"
    path_to_cloud = "Путь на архив в облаке: {remote_path}"
    permission_error = "[Поиск программы 7z]. Нет доступа к {path}"
    prompt = "{var} = {current}, введите новое или Enter, чтобы оставить прежнее:"
    start_full_auth_flow = "Запуск полного процесса аутентификации"
    start_create_archive = "Начало создания архива"
    start_fast_load = "Начало быстрой загрузки файла {local_path}"
    start_load_file = "Начало загрузки файла {local_path}"
    start_main = "Запуск процесса резервного копирования"
    start_send_email = "Отправка email: {subject}"
    start_update_token = "Начало формирование токена доступа посредством refresh_token"
    start_update_tokens = "Получаем токены от Яндекс с помощью refresh_token"
    starting_archiving = "Запуск архивации: {cmd}"
    successful = "Корректное завершение работы"
    successful_access_token = "Успешно получен access_token"
    successful_archiving = "Архивация завершена успешно"
    successful_send_email = "Служебное сообщение отправлено по e-mail"
    task_error = "Задание завершено с ошибками уровня {name_max_level}"
    task_successfully = "Задание успешно завершено!"
    task_warnings = "{name_max_level} --> Задание завершено с предупреждениями"
    time_run = "Время выполнения: {time} сек"
    token_expired = "[Token Load] Токен истек {seconds} сек назад"
    token_in_memory = "Используется существующий валидный токен"
    token_invalid = "Токен недействителен. Код ответа API Яндекс-Диска: {status}"
    token_valid = "Токен успешно прошел проверку через API"
    tokens_saved = "Токены сохранены в keyring"
    updated_tokens = "С помощью refresh_token получены обновлённые токены от Яндекс."
    updated_tokens_error = (
        "Не удалось получить обновлённые токены от Яндекс с помощью refresh_token. {e}"
    )
    url_received = "Получен upload URL: {upload_url}"
    valid_token = "Токен успешно получен"
    valid_token_found = "[Token Load] Найден валидный {token} в keyring"
