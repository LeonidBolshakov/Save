from __future__ import annotations
import os
import logging

logger = logging.getLogger(__name__)

from SRC.YADISK.OAUTH.exceptions import AuthError
from SRC.YADISK.OAUTH.oauthflow import OAuthFlow
from SRC.YADISK.yandextextmessage import YandexTextMessage as YT


class YandexOAuth:
    """Фасадный класс для OAuth авторизации в Яндекс-Диск.

    Предоставляет упрощенный интерфейс для получения access token,
    инкапсулируя всю логику OAuth 2.0 с PKCE.

    Attributes:
        flow (OAuthFlow): OAuth 2.0 flow processor
    """

    def __init__(
            self,
    ):
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        self.flow = OAuthFlow()

    def get_access_token(self) -> str | None:
        """Получает действительный access token"""
        try:
            token = self.flow.get_access_token()
            if token:
                logger.info(YT.successful_access_token)
                return token
            else:
                raise AuthError(YT.failed_access_token)
        except Exception as e:
            raise AuthError(YT.critical_error.format(e=e))
