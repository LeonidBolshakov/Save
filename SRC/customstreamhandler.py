import logging


class CustomStreamHandler(logging.StreamHandler):
    def __init__(self, stream=None):
        super().__init__(stream)

    def emit(self, record):
        """
        Переопределение метода записи лога
        :param record: запись лога
        """
        # Проверка наличия запрещенной фразы в сообщении
        if "*Stop*" not in record.getMessage():
            # Корректный вызов родительского метода
            super().emit(record)
