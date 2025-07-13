import logging

logger = logging.getLogger(__name__)

import yagmail
from yagmail.error import YagAddressError, YagInvalidEmailAddress

# Константы
SMTP_HOST = "smtp.yandex.ru"
SMTP_PORT = 465


class YaGmailHandler:
    """Обработчик для отправки email через yagmail"""

    def __init__(self, sender_email: str, sender_password: str, recipient_email: str):
        self._validate_credentials(sender_email, sender_password, recipient_email)
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email

    @staticmethod
    def _validate_credentials(sender: str, password: str, recipient: str) -> None:
        """Проверяет наличие обязательных учетных данных"""
        if not all([sender, password, recipient]):
            error_msg = "В файле .env отсутствуют учетные данные электронной почты"
            logging.critical(error_msg)
            raise ValueError(error_msg)

    def send_email(self, subject: str, content: str) -> bool:
        """Отправляет email с обработкой ошибок"""
        try:
            with yagmail.SMTP(
                user=self.sender_email,
                password=self.sender_password,
                host=SMTP_HOST,
                port=SMTP_PORT,
                smtp_ssl=True,
            ) as yag:
                yag.send(to=self.recipient_email, subject=subject, contents=content)
            return True
        except (YagAddressError, YagInvalidEmailAddress) as e:
            logging.critical(f"Ошибка в email адресе: {e}")
        except Exception as e:
            logging.error(f"Ошибка отправки email: {e}")
        return False
