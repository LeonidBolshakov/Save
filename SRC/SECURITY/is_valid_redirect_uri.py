from urllib.parse import urlparse
import re

from SRC.GENERAL.textmessage import TextMessage as T


def is_valid_redirect_uri(uri: str) -> bool:
    """Проверяет валидность redirect URI согласно спецификации OAuth 2.0 и требованиям Яндекс.

    Args:
        uri (str): URI для проверки (например, "http://localhost:8080/callback")

    Returns:
        bool: True если URI валиден, False если есть нарушения

    Raises:
        ValueError: Если URI содержит явно опасные конструкции

    Note:
        Соответствует RFC 6749 (OAuth 2.0) и требованиям Яндекс API:
        - Запрещены фрагменты (#)
        - Для localhost разрешены нешифрованные соединения (http)
        - Домен должен быть валидным
    """
    if not uri:
        return False

    try:
        parsed = urlparse(uri)
    except ValueError:
        return False

    # 1. Проверка схемы (протокола)
    if parsed.scheme not in ("http", "https"):
        return False

    # 2. Для localhost разрешаем только HTTP (в development)
    if parsed.hostname == "localhost" and parsed.scheme != "http":
        return False

    # 3. Проверка домена (требования Яндекса)
    if not re.match(
            r"^(localhost|([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+\.[a-zA-Z]{2,})$",
            parsed.hostname or "",
    ):
        return False

    # 4. Запрет фрагментов (#section) согласно RFC 6749
    if parsed.fragment:
        return False

    # 5. Проверка порта (если указан)
    if parsed.port is not None and not (1 <= parsed.port <= 65535):
        return False

    # 6. Базовые проверки пути и параметров
    if "//" in parsed.path:  # Запрет путей с двойным слешем
        return False

    # 7. Проверка на опасные символы
    if re.search(r'[<>"\'\s]', uri):  # Запрет HTML-тегов и кавычек
        raise ValueError(T.dangerous_symbols)

    # 8. Дополнительные требования Яндекса
    if len(uri) > 200:  # Максимальная длина URI
        return False

    return True
