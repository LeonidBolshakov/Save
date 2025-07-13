import logging
from messagemail import MessageMail


class MaxLevelHandler(logging.Handler):
    """Подсчитывает максимальный уровень логов и в конце работы отправляет e-mail"""

    highest_level = 0  # Атрибут класса (общий для всех экземпляров)

    def __init__(self):
        super().__init__()
        self.permanent_lock = False

    def emit(self, record: logging.LogRecord) -> None:
        """Обрабатывает запись лога"""
        if self.permanent_lock:
            return

        if "*Stop*" in record.getMessage():
            self.permanent_lock = True
            message_mail = MessageMail()
            message_mail.compose_and_send_email(record, self.highest_level)
        elif record.levelno > self.highest_level:
            self.__class__.highest_level = record.levelno

    def get_highest_level(self) -> int:
        """
        Возвращает из всех сообщений об ошибке.
        :return: (int) - максимальное значение уровня ошибки
        """
        return self.highest_level
