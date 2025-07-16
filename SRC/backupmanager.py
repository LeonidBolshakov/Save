import sys
import logging
from dotenv import load_dotenv
import os
from tempfile import TemporaryDirectory

logger = logging.getLogger(__name__)

from file7zarchiving import File7ZArchiving
from yandex_disk import YandexDisk
from maxlevelhandler import MaxLevelHandler
from constant import Constant as C
from messagemail import MessageMail


class BackupManager:
    """Класс для управления процессом резервного копирования данных.

    Обеспечивает:
    - Проверку необходимых переменных окружения
    - Создание локального архива с данными
    - Загрузку архива на Яндекс-Диск
    - Обработку ошибок и логирование процесса
    """

    def main(self) -> None:
        """Основной метод выполнения полного цикла резервного копирования.

        Процесс включает:
        1. Проверку переменных окружения
        2. Создание временной директории
        3. Создание локального архива
        4. Загрузку архива на Яндекс-Диск
        5. Завершение с соответствующим статусом

        Логирует все этапы процесса и обрабатывает возможные ошибки.
        """
        logger.info("Начало процесса архивации и сохранения файлов в облако")
        try:
            # Используем TemporaryDirectory для автоматической очистки временных файлов
            with TemporaryDirectory() as temp_dir:
                local_archive = File7ZArchiving()
                local_path = local_archive.make_local_archive(temp_dir)
                remote_path = self.write_file(local_path)
                self.completion(failure=False, remote_path=remote_path)
        except Exception as e:
            logger.exception(
                f"*** Критическая ошибка при выполнении резервного копирования {e}"
            )
            self.completion(failure=True)

    @staticmethod
    def write_file(local_path: str) -> str:
        """Загружает файл на Яндекс-Диск используя API Яндекс.

        Args:
            local_path: Абсолютный путь к локальному файлу для загрузки

        Returns:
            str: Путь к загруженному файлу на Яндекс-Диске

        Raises:
            OSError: Если загрузка файла не удалась
            RuntimeError: При проблемах с API Яндекс-Диска
        """
        yandex_disk = YandexDisk()
        logger.info("Инициализация загрузки файла на Яндекс.Диск")

        try:
            if not (_remote_path := yandex_disk.write_file_fast(local_path)):
                error_msg = "API Яндекс.Диска не вернуло путь к файлу"
                logger.critical(error_msg)
                raise OSError(error_msg)

            logger.info(f"Архив успешно загружен по пути: {_remote_path}")
            return _remote_path
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {str(e)}")
            raise RuntimeError("Ошибка загрузки на Яндекс.Диск") from e

    # noinspection PyUnusedLocal
    def completion(self, failure: bool, remote_path: str | None = None) -> None:
        """Завершает работу программы с соответствующим статусом.

        Логирует результат выполнения и вызывает завершение программы
        с кодом 0 (успех) или 1 (ошибка). Также формирует специальное
        сообщение для системы отправки email-уведомлений.

        Args:
            failure: Флаг неудачного завершения операции
            remote_path: Путь к файлу на Яндекс-Диске (для уведомления)
        """
        handler = MaxLevelHandler()
        max_level = handler.get_highest_level()
        name_max_level = logging.getLevelName(max_level)

        if failure:
            logger.error(f"{name_max_level.upper()} --> Задание провалено")
        else:
            self.completion_log(max_level, name_max_level)

        # Специальное сообщение для системы уведомлений
        logger.critical(f"{C.STOP_SERVICE_MESSAGE}{remote_path}")
        message_mail = MessageMail()
        message_mail.compose_and_send_email()
        sys.exit(1 if failure else 0)

    @staticmethod
    def completion_log(max_level: int, name_max_level: str) -> None:
        """Логирует итоговый результат выполнения задания.

        В зависимости от максимального уровня залогированных ошибок
        формирует соответствующее сообщение в лог.

        Args:
            max_level: Числовой код максимального уровня ошибки
            name_max_level: Текстовое название уровня ошибки
        """
        match max_level:
            case logging.NOTSET | logging.DEBUG | logging.INFO:
                logger.info("Задание успешно завершено!")
            case logging.WARNING:
                logger.warning(
                    f"{name_max_level.upper()} --> Задание завершено с предупреждениями"
                )
            case logging.ERROR | logging.CRITICAL:
                logger.error(
                    f"Задание завершено с ошибками уровня {name_max_level.upper()}"
                )
