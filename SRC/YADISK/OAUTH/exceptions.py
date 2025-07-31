class AuthError(Exception):
    """Базовое исключение для ошибок авторизации."""


class AuthCancelledError(AuthError):
    """Пользователь отменил авторизацию или истек таймаут."""


class RefreshTokenError(AuthError):
    """Ошибка при обновлении токена (невалидный или отозванный refresh token)."""
