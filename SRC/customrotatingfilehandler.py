import logging.handlers


class CustomRotatingFileHandler(logging.handlers.RotatingFileHandler):
    def __init__(
        self, filename, mode="a", maxBytes=0, backupCount=0, encoding=None, delay=False
    ):
        """
        Инициализация обработчика
        :param filename: путь к файлу лога (обязательный)
        :param mode: режим открытия файла
        :param maxBytes: максимальный размер файла перед ротацией
        :param backupCount: количество хранимых бэкапов
        :param encoding: кодировка файла
        :param delay: отложенное открытие файла
        """
        super().__init__(
            filename=filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )

    def emit(self, record: logging.LogRecord):
        """
        Переопределение метода записи лога
        :param record: запись лога
        """
        # Проверка наличия запрещенной фразы в сообщении
        if "*Stop*" not in record.getMessage():
            # Корректный вызов родительского метода
            super().emit(record)
