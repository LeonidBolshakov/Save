import sys
from tempfile import TemporaryDirectory
import time
import logging

logger = logging.getLogger(__name__)

from SRC.ARCHIVES.file7zarchiving import File7ZArchiving
from SRC.YADISK.yandex_disk import YandexDisk
from SRC.LOGGING.tunelogger import TuneLogger  # Для настройки системы логирования
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.MAIL.messagemail import MessageMail
from SRC.GENERAL.constant import Constant as C
from SRC.GENERAL.textmessage import TextMessage as T


class BackupManager:
    """Класс для управления процессом резервного копирования данных.

    Обеспечивает:
    - Создание локального архива с данными
    - Загрузку архива на Яндекс-Диск
    - Обработку ошибок и логирование процесса
    """

    @staticmethod
    def validate_vars_environments():
        logging.basicConfig(
            level=logging.INFO,
            format=C.LOG_FORMAT,
        )  # Настройка логирования только для использования до настройки основного логирования

        EnvironmentVariables().validate_vars()  # Проверка наличия переменных окружения

        for (  # Подготовка к настройке основного логирования
                handler
        ) in logging.root.handlers:  # Отказ от предыдущей настройки на логирование
            logging.root.removeHandler(handler)
        # noinspection PyUnusedLocal

    def completion(self, remote_path: str | None = None) -> None:
        """Завершает работу программы с соответствующим статусом.

        Логирует результат выполнения и вызывает завершение программы
        с кодом 0 (успех) или 1 (ошибка). Также формирует специальное
        сообщение для системы отправки email-уведомлений.

        Args:
            remote_path: Путь к файлу на Яндекс-Диске (для уведомления)
        """
        handler = MaxLevelHandler()
        max_level = handler.get_highest_level()
        name_max_level = logging.getLevelName(max_level)

        self.start_completion_work(remote_path=remote_path, max_level=max_level)
        self.completion_log(max_level, name_max_level)
        sys.exit(1 if logging.ERROR <= max_level else 0)

    @staticmethod
    def start_completion_work(remote_path: str, max_level: int) -> None:
        # Специальное сообщение для системы уведомлений
        logger.critical(f"{C.STOP_SERVICE_MESSAGE}{remote_path}")
        message_mail = MessageMail()
        message_mail.compose_and_send_email()

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
                logger.info(T.task_successfully)
            case logging.WARNING:
                logger.warning(
                    T.task_warnings.format(name_max_level=name_max_level.upper())
                )
            case logging.ERROR:
                logger.error(T.task_error.format(name_max_level=name_max_level.upper()))
            case logging.CRITICAL:
                logger.critical(
                    T.task_error.format(name_max_level=name_max_level.upper())
                )

    def main(self):
        """
        Выполняет:
        1. Настройку системы логирования
        2. Запуск основного процесса создания и загрузки резервных копий

        Логирует все этапы работы и обрабатывает возможные ошибки.
        """
        self.validate_vars_environments()  # Проверка наличия переменных окружения
        TuneLogger().setup_logging()  # Настройка системы логирования

        logger.info(T.start_main)
        start_time = time.time()

        remote_path = None
        try:
            remote_path = self.get_remote_path()  # Запуск основного процесса
        except KeyboardInterrupt:
            logger.error(T.canceled_by_user, exc_info=True)
            raise
        except Exception as e:
            logger.error(
                T.critical_error_type.format(type=e.__class__.__name__, e=e),
                exc_info=True,
            )
        finally:
            self.completion(remote_path=remote_path)
            logger.info(T.time_run.format(time=f"{time.time() - start_time:.2f}"))

    def get_remote_path(self) -> str:
        """Основной метод выполнения полного цикла резервного копирования.

        Процесс включает:
        1. Создание временной директории
        2. Создание локального архива во временной директории
        3. Загрузку локального архива на Яндекс-Диск
        4. Возвращает путь на сформированный архив, перенесённый в облако

        Логирует все этапы процесса и обрабатывает возможные ошибки.
        """
        logger.info(T.init_main)
        remote_path = None
        try:
            # Используем TemporaryDirectory для автоматической очистки временных файлов
            with TemporaryDirectory() as temp_dir:
                local_archive = File7ZArchiving()
                local_path = local_archive.make_local_archive(temp_dir)
                remote_path = self.write_file(local_path)
                return remote_path

        except Exception as e:
            raise

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
        logger.info(T.init_load_to_disk)
        variables = EnvironmentVariables()
        try:
            port = int(variables.get_var(C.ENV_YANDEX_PORT))
        except ValueError as e:
            logger.critical("")
            raise ValueError(T.invalid_port.format(e=e)) from e

        yandex_disk = YandexDisk(port=port)

        try:
            if not (_remote_path := yandex_disk.write_file_fast(local_path)):
                logger.critical("")
                raise OSError(T.error_API_Yandex_disk)

            return _remote_path
        except Exception as e:
            raise
