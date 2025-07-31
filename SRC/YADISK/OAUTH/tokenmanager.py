from __future__ import annotations
import time
import requests
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.YADISK.OAUTH.exceptions import AuthError
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT
from SRC.YADISK.yandexconst import YandexConstants as YC


class TokenManager:
    """Управляет жизненным циклом OAuth-токенов для Яндекс-Диска.

    Отвечает за:
    - Сохранение и загрузку токенов из secure storage (keyring)
    - Проверку валидности и срока действия токенов
    - Взаимодействие с API Яндекс-Диска для проверки токенов

    Attributes:
        variables (EnvironmentVariables): Обертка для работы с переменными окружения и keyring
    """

    def __init__(self) -> None:
        self.variables = EnvironmentVariables()

    def save_tokens(
            self, access_token: str, refresh_token: str | None, expires_at: str
    ) -> None:
        """Сохраняет токены и время жизни токена в secure storage.

        Args:
            access_token (str): Токен для API-запросов
            refresh_token (str): Токен для обновления access token
            expires_at (str): Время окончания действия токена для API-запросов

        Note:
            Автоматически вычитает 60 секунд из expires_in для раннего обновления
        """
        try:
            # Сохраняем токены и время истечения в памяти (keyring)
            self.variables.put_keyring_var(YC.YANDEX_ACCESS_TOKEN, access_token)
            self.variables.put_keyring_var(YC.YANDEX_EXPIRES_AT, expires_at)
            if refresh_token:
                self.variables.put_keyring_var(YC.YANDEX_REFRESH_TOKEN, refresh_token)

            logger.debug(YT.tokens_saved)

        except Exception as e:
            raise AuthError(YT.error_saving_tokens.format(e=e))

    def get_vars(self) -> tuple[str, str, str] | None:
        access_token = self.variables.get_var(YC.YANDEX_ACCESS_TOKEN)
        refresh_token = self.variables.get_var(YC.YANDEX_REFRESH_TOKEN)
        expires_at = self.variables.get_var(YC.YANDEX_EXPIRES_AT)

        logger.debug(
            f"[Token Load] {YC.YANDEX_ACCESS_TOKEN}: {YC.PRESENT if access_token else YC.MISSING}"
        )
        logger.debug(
            f"[Token Load] {YC.YANDEX_REFRESH_TOKEN}: {YC.PRESENT if refresh_token else YC.MISSING}"
        )
        logger.debug(
            f"[Token Load] {YC.YANDEX_EXPIRES_AT}: {YC.PRESENT if expires_at else YC.MISSING}"
        )

        return access_token, refresh_token, expires_at

    @staticmethod
    def _valid_expires_at(expires_at: str) -> bool:
        try:
            expires_at_float = float(expires_at)
        except (TypeError, ValueError) as e:
            logger.warning(YT.not_float.format(e=e))
            return False

        current_time = time.time()
        if current_time >= expires_at_float:
            seconds = f"{current_time - expires_at_float:.0f}"
            logger.info(YT.token_expired.format(seconds=seconds))
            return False

        return True

    def load_and_validate_exist_tokens(self) -> dict[str, str] | None:
        """Загружает и проверяет токены из keyring"""
        try:
            _vars = self.get_vars()

            if _vars is None:
                return None

            access_token, refresh_token, expires_at = _vars

            if not all([access_token, expires_at]):
                return None

            if not self._valid_expires_at(expires_at):
                return None

            if not self._validate_token_api(access_token):
                return None

            logger.debug(YT.valid_token_found.format(token=YC.YANDEX_ACCESS_TOKEN))
            return {
                YC.YANDEX_ACCESS_TOKEN: access_token,
                YC.YANDEX_REFRESH_TOKEN: refresh_token,
                YC.YANDEX_EXPIRES_AT: expires_at,
            }

        except Exception as e:
            logger.warning(YT.error_load_tokens.format(e=e))
            return None

    @staticmethod
    def _validate_token_api(access_token: str) -> bool:
        """Проверяет валидность токена через API Яндекс-Диска"""
        try:
            response = requests.get(
                YC.URL_API_YANDEX_DISK,
                headers={"Authorization": f"OAuth {access_token}"},
                timeout=5,
            )

            if response.status_code == 200:
                logger.debug(YT.token_valid)
                return True

            logger.warning(YT.token_invalid.format(status=response.status_code))
            return False

        except requests.RequestException as e:
            logger.warning(YT.error_check_token.format(e=e))
            return False
