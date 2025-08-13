import logging.handlers
import logging

logger = logging.getLogger(__name__)

from SRC.GENERAL.constants import Constants as C


class CustomRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Кастомный обработчик логов с ротацией файлов и фильтрацией сообщений.

    Наследует стандартную функциональность RotatingFileHandler и добавляет:
    - Фильтрацию сообщений по ключевой фразе
    - Безопасную обработку ошибок записи
    - Безопасную обработку ошибок записи
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
    ):
        """
        Инициализирует обработчик логов.

        Args:
            filename: Путь к файлу лога
            mode: Режим открытия файла (по умолчанию 'a' - append)
            maxBytes: Максимальный размер файла перед ротацией (0 - отключено)
            backupCount: Количество сохраняемых бэкапов (0 - бесконечно)
            encoding: Кодировка файла
            delay: Отложенное открытие файла
        """
        super().__init__(
            filename=filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
        )
        self.email_send_trigger = C.ARCHIVING_END_TRIGGER

    def emit(self, record: logging.LogRecord) -> None:
        """
        Записывает лог-запись с фильтрацией запрещенных фраз.

        Args:
            record: Объект лог-записи

        Note:
            - Автоматически обрабатывает ротацию файлов через родительский класс
            - Пропускает записи, содержащие FORBIDDEN_PHRASE
            - Обрабатывает ошибки записи
        """
        try:
            # Фильтрация сообщений
            if self.email_send_trigger not in record.getMessage():
                if len(record.getMessage()):
                    # Ротация и запись обрабатываются родительским классом
                    super().emit(record)

        except Exception:
            logger.exception("...")
            self.handleError(record)
