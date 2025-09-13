class YandexTextMessage(frozenset):
    authorization_error = "Ошибка авторизации {e}"
    authorization_timeout = "Превышено время ожидания авторизации {e}"
    callback_timeout = "Таймаут ожидания ответа от Яндекс во время авторизации"
    canceled_authorization = "Отмена авторизации пользователем"
    critical_error = "Критическая ошибка во время получения токена: {e}"
    dangerous_symbols = "Ответ от Яндекс (Redirect URI) содержит опасные символы"
    dictionary_expected = (
        "От Яндекс ожидался словарь, получен тип {type}.\n{response}..."
    )
    during = "Файл загружен за {during} сек."
    error_API_Yandex_disk = "Файл на Яндекс-Диск не записан"
    error_check_token = "Яндекс не принял наш токен: {e}"
    error_create_directory_ya_disk = "Ошибка создания директории на Яндекс-Диск: {e}"
    error_hash = (
        "Файл {file} записан на Яндекс-Диск, но записан с ошибкой.\n"
        "Приступаем к удалению файла и, возможно, повторной записи"
    )
    error_load_file = "Ошибка при загрузке файла на Яндекс-Диск: {err}"
    error_load_tokens = (
        "[Token Load] Ошибка загрузки закрытой информации из keyring: {e}"
    )
    error_network = "Ошибка Internet при загрузке файла в облако: {e}"
    error_processing_request = "Ошибка авторизации Яндекс: {e}"
    error_refresh_token = (
        "Яндекс отказал обновить токена доступа с помощью refresh токена. "
        "\nСтатус код - {status_code}"
    )
    error_saving_tokens = "Ошибка сохранения закрытой информации в keyring: {e}"
    error_upload_URL = "Яндекс не выдал URL для быстрой загрузки на Яндекс-Диск."
    error_ya_disk = "Ошибка Яндекс.Диска: {e}"
    expires_in_error = (
        "В токен доступа, полученном от Яндекса, время жизни токена не число {key}"
    )
    failed_access_token = "Яндекс не выдал токен доступа"
    fast_load = "Быстрая загрузка файла {local_path}"
    finish_load = "Загрузка завершена: {local_path} → {remote_path}"
    folder_created = "Папка {current_path} создана на Яндекс-Диске"
    folder_not_found = "Папка {remote_dir} не найдена, создаем"
    get_token = "Получение токена авторизации"
    get_token_error = "Ошибка Яндекса при выдаче токена авторизации: {e}"
    init_load_to_disk = "Начало загрузки файла на Яндекс.Диск"
    invalid_port = "В, сохранённом нами на компьютере, REDIRECT_URI не задан, или задан как не целое число, номер порта. {e}"
    invalid_request = "Некорректный запрос для создания доступа к Яндекс-Диску"
    invalid_token = "Яндекс отклонил токен доступа к Яндекс.Диск!"
    load = "Загрузка {local_path} -> {remote_path}"
    loaded_token = "Будут использоваться сохраненные закрытые данные"
    load_success = "Файл {local_path} успешно загружен на Яндекс-Диск в {remote_path}"
    local_file_not_found = "Локальный файл не найден: {path}"
    mismatch_MD5 = "Несовпадение контрольной суммы(MD5) для {remote_path}— возможно попробуем ещё раз"
    no_auth_code = "В присланной Яндекс информации нет кода авторизации"
    no_callback_path = "Яндекс не авторизовал наш запрос."
    no_correct_redirect_uri = (
        "Заданный нами в keyring -  redirect_uri: {redirect_uri}.\n"
        "Должен соответствовать зарегистрированному в \n"
        "кабинете разработчика Яндекса"
    )
    no_expires_in = (
        "expires_in (время жизни токена) нет в токен полученном от Яндекс.\n"
        "Полагаем, что время жизни не ограничено."
    )
    no_internet = "Нет подключения к интернету -> Нет доступа к Яндекс-Диску\n{e}"
    no_token_in_response = (
        "Токен доступа не получен в ответе Яндекса\n" "Ошибка в Internet или программе"
    )
    no_valid_token = "Все попытки получить доступ к Яндекс-Диску, включая полную аутентификацию провалились."
    not_float = "[Token Load] Возможно ошибка Internet. Время истечения токена не число с плавающей запятой: {e}"
    not_valid_json = "Возможно ошибка Internet. В ответе Яндекс неверный JSON: {e}. Ответ: {response}"
    start_fast_load = "Начало быстрой загрузки файла {local_path}"
    start_full_auth_flow = "Запуск полного процесса аутентификации"
    start_update_token = "Начало формирование токена доступа посредством refresh_token"
    start_update_tokens = "Получаем токены от Яндекс с помощью refresh_token"
    successful_access_token = "Успешно получен access_token"
    token_expired = "[Token Load] Срок действия токена истек {seconds} сек назад"
    token_in_memory = "Используется существующий валидный токен"
    token_invalid = (
        "Токен, хранящийся в keyring, недействителен.\n"
        "Код статуса ответа API Яндекс: {status}"
    )
    token_valid = "Токен успешно прошел проверку через API Яндекса"
    tokens_saved = "Токены сохранены в keyring"
    unknown_error = "Ошибка доступа кcls Яндекс-Диску: {e}"
    unknown_format = "Неизвестный формат для ссылки для прямой загрузки файла на Яндекс-Диск:\n {type} -> {res}"
    valid_token = "Токен успешно получен"
    valid_token_found = "[Token Load] Найден валидный {token} в keyring"
    updated_tokens = "С помощью refresh_token получены обновлённые токены от Яндекс."
    updated_tokens_error = (
        "Не удалось получить обновлённые токены от Яндекс с помощью refresh_token. {e}"
    )
    url_received = "Получен адрес прямой загрузки файла в облако: {upload_url}"
