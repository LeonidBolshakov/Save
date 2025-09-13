import logging

from SRC.GENERAL.constants import Constants as C

logger = logging.getLogger(__name__)


class MaxLevelHandler(logging.Handler):
    """Кастомный обработчик логов, который:
    1. Отслеживает максимальный уровень полученных сообщений
    2. Автоматически инициирует отправку email-уведомления при получении специального маркера
    3. Блокирует дальнейшую обработку после отправки уведомления

    Атрибуты класса:
        highest_level (int): Максимальный зарегистрированный уровень логирования (общий для всех экземпляров)
                           Значения соответствуют стандарту logging: CRITICAL=50, ERROR=40, WARNING=30 и т.д.

    Атрибуты экземпляра:
        permanent_lock (bool): Флаг блокировки обработки новых сообщений после отправки уведомления
    """

    highest_level = logging.NOTSET  # Начальное значение (NOTSET=0)
    last_time = 0.0
    remote_archive_path = ""

    def __init__(self):
        """Инициализирует обработчик логов."""
        super().__init__()
        self.permanent_lock = False  # Флаг блокировки обработки
        self.archiving_end_trigger = C.ARCHIVING_END_TRIGGER
        self.remote_link = C.LINK_REMOTE_ARCHIVE

    def emit(self, record: logging.LogRecord) -> None:
        """Обрабатывает каждую запись лога.

        Логика работы:
        1. Если установлен permanent_lock - пропускает обработку
        2. Если в сообщении есть маркер "*Stop*" - инициирует отправку email
        3. Иначе обновляет highest_level, если уровень текущей записи выше

        Args:
            record (logging. LogRecord): Объект записи лога, содержащий все детали сообщения

        Примечание:
            После отправки email устанавливает permanent_lock=True для предотвращения повторных отправок
        """
        if self.permanent_lock:
            return

        message = record.getMessage()

        # Триггер отправки email
        if self.archiving_end_trigger in message:
            self.permanent_lock = True
            self.__class__.last_time = record.created
            self.__class__.remote_archive_path = self._extract_archive_path(message)
            return

        if record.levelno >= self.__class__.highest_level:
            self.__class__.highest_level = record.levelno

    def get_highest_level(self) -> int:
        """Возвращает максимальный уровень зарегистрированных сообщений.

        Returns:
            int: Числовое значение максимального уровня (соответствует logging.LEVEL)

        Пример:
            >>> handler = MaxLevelHandler()
            >>> handler.get_highest_level()
            0  # NOTSET
        """
        return self.__class__.highest_level

    def get_last_time(self) -> float:
        """Возвращает время последнего результативного обращения к методу.

        Returns:
            float: Время последнего результативного обращения (record.created).
            Результативным называем обращение, для которого self.permanent_lock (флаг блокировки) = False
        """
        return self.__class__.last_time

    def get_remote_archive_path(self):
        """Возвращает путь к архиву в облаке.

        Returns:
            str - Путь к архиву в облаке.
        """
        return self.__class__.remote_archive_path

    def _extract_archive_path(self, message: str) -> str:
        """Извлекает путь к архиву из строки лога.

        Ожидает строку в формате: "...remote_path=<путь>..."
        """
        try:
            if self.remote_link in message:
                # Берем текст после 'remote_path=' до первого пробела
                return message.split(self.remote_link)[1].split()[0]
            return ""
        except Exception:
            logger.exception("...")
            return ""
