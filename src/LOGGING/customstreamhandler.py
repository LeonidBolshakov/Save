import logging
import sys
from io import TextIOWrapper
from typing import TextIO

from src.GENERAL.constants import Constants as C


class CustomStreamHandler(logging.StreamHandler):
    def __init__(self, stream: TextIO | None = None):
        if stream is None:
            stream = sys.stderr

        if isinstance(stream, TextIOWrapper):
            stream.reconfigure(encoding="utf-8")

        super().__init__(stream)

        self.email_send_trigger = C.ARCHIVING_END_TRIGGER

    def emit(self, record: logging.LogRecord) -> None:
        """
        Переопределение метода записи лога для фильтрации сообщений.
        """
        try:
            message = record.getMessage()

            if message and self.email_send_trigger not in message:
                super().emit(record)

        except Exception:
            self.handleError(record)
