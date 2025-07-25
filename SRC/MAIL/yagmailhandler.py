import yagmail  # type: ignore
from yagmail.error import YagAddressError, YagInvalidEmailAddress  # type: ignore
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class YaGmailHandler:
    """Обработчик для отправки email через yagmail"""

    def __init__(self, sender_email: str, sender_password: str, recipient_email: str):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    def send_email(self, subject: str, content: str) -> bool:
        """Отправляет email с обработкой ошибок"""
        try:
            with yagmail.SMTP(
                user=self.sender_email,
                password=self.sender_password,
                host=C.YANDEX_SMTP_HOST,
                port=C.YANDEX_SMTP_PORT,
                smtp_ssl=True,
            ) as yag:
                yag.send(to=self.recipient_email, subject=subject, contents=content)
            return True
        except (YagAddressError, YagInvalidEmailAddress) as e:
            logging.critical(T.error_address_email.format(e))
        except Exception as e:
            logging.warning(T.error_send_email.format(e))
        return False
