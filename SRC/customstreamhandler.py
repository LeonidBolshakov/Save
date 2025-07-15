import logging
from constant import Constant as C

class CustomStreamHandler(logging.StreamHandler):

    def __init__(self, stream=None):
        super().__init__(stream)
        self.stream = stream
        self.email_send_trigger = C.EMAIL_SEND_TRIGGER

    def emit(self, record):
        """
        Переопределение метода записи лога для фильтрации сообщений.

        Args:
            record (logging. LogRecord): Запись лога для обработки
        """
        try:
            if self.email_send_trigger not in record.getMessage():
                super().emit(record)
        except Exception:
            self.handleError(record)
