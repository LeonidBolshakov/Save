from SRC.YADISK.yandexconst import YandexConstants as YC


class YandexTextMessage(frozenset):
    authorization_error = "Ошибка авторизации {e}"
    authorization_timeout = "Превышено время ожидания авторизации {e}"
    callback_timeout = "Таймаут ожидания callback"
    canceled_authorization = "Отмена авторизации пользователем"
    critical_error = "Критическая ошибка: {e}"
    dangerous_symbols = "Redirect URI содержит опасные символы"
    dictionary_expected = "Ожидался словарь, получен {type}.\nОтвет: {response}..."
    during = "Файл загружен за {during} сек."
    error_API_Yandex_disk = "API Яндекс.Диска не вернуло путь к файлу"
    error_check_token = "Ошибка проверки токена доступа через API: {e}"
    error_create_directory_ya_disk = "Ошибка создания директории на Яндекс-Диск: {e}"
    error_load_file = "Ошибка при загрузке файла: {err}"
    error_load_tokens = (
        "[Token Load] Ошибка загрузки закрытой информации из keyring: {e}"
    )
    error_processing_request = "Ошибка обработки запроса авторизации Яндекс: {e}"
    error_refresh_token = "Ошибка {status_code} при обновлении токена доступа с помощью refresh токена- {e}"
    error_saving_tokens = "Ошибка сохранения закрытой информации в keyring: {e}"
    error_upload_URL = (
        "Ошибка получения upload URL для быстрой загрузки на Яндекс-Диск."
    )
    error_ya_disk = "Ошибка Яндекс.Диска: {e}"
    expires_in = "В токен доступа, полученном с сервера время жизни токена равно {expires_in} сек."
    expires_in_error = "В токен доступа, полученном с сервера время жизни токена не плавающее число {key}"
    failed_access_token = "Не удалось получить токен доступа"
    fast_load = "Быстрая загрузка файла {local_path}"
    folder_created = "Папка {archive_path} создана"
    folder_not_found = "Папка {archive_path} не найдена, создаем"
    get_token = "Получение токена авторизации"
    get_token_error = "Ошибка получения токена авторизации: {e}"
    init_load_to_disk = "Инициализация загрузки файла на Яндекс.Диск"
    invalid_port = (
            "В переменных окружения не задан, или задан как не целое число, номер порта, заданный в приложении Яндекс. "
            + f"Имя переменной окружения - {YC.ENV_YANDEX_PORT}. "
            + "{e}"
    )
    invalid_request = "Некорректный запрос для создания доступа к Яндекс-Диску"
    invalid_token = "Недействительный токен доступа к Яндекс.Диск!"
    load = "Загрузка {local_path} -> {remote_path}"
    loaded_token = "Будут использоваться сохраненные закрытые данные"
    load_success = "Файл {local_path} успешно загружен в {remote_path}"
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
    no_internet = "Нет подключения к интернету -> Нет доступа к Яндекс-Диску"
    no_refresh_token = (
        "Refresh token отсутствует/n"
        "Восстановление токена доступа с помощью refresh токена отменено."
    )
    no_token_in_response = (
        "Токен доступа не получен в ответе сервера\n"
        "Недействительный токен или ошибка в Internet"
    )
    no_valid_token = "Токен недействителен. Нет доступа к Яндекс-Диск."
    not_float = "[Token Load] Время истечения токена не число с плавающей запятой: {e}"
    not_valid_json = "Невалидный JSON: {e}. Ответ: {response}"
    start_fast_load = "Начало быстрой загрузки файла {local_path}"
    start_full_auth_flow = "Запуск полного процесса аутентификации"
    start_update_token = "Начало формирование токена доступа посредством refresh_token"
    start_update_tokens = "Получаем токены от Яндекс с помощью refresh_token"
    successful_access_token = "Успешно получен access_token"
    token_expired = "[Token Load] Токен истек {seconds} сек назад"
    token_in_memory = "Используется существующий валидный токен"
    token_invalid = "Токен недействителен. Код ответа API Яндекс-Диска: {status}"
    token_valid = "Токен успешно прошел проверку через API"
    tokens_saved = "Токены сохранены в keyring"
    unknown_error = "Неизвестная ошибка доступа у Яндекс-Диску: {e}"
    valid_token = "Токен успешно получен"
    valid_token_found = "[Token Load] Найден валидный {token} в keyring"
    updated_tokens = "С помощью refresh_token получены обновлённые токены от Яндекс."
    updated_tokens_error = (
        "Не удалось получить обновлённые токены от Яндекс с помощью refresh_token. {e}"
    )
    url_received = "Получен URL загрузки: {upload_url}"
