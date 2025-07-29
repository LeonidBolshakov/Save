import sys
from tempfile import TemporaryDirectory
import time
import traceback
import logging

logger = logging.getLogger(__name__)

from SRC.ARCHIVES.file7zarchiving import File7ZArchiving
from SRC.LOGGING.tunelogger import TuneLogger  # Для настройки системы логирования
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.MAIL.messagemail import MessageMail
from SRC.GENERAL.managerwritefile import write_file
from SRC.GENERAL.constants import Constants as C
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

        try:
            EnvironmentVariables().validate_vars()  # Проверка наличия переменных окружения

            for (  # Подготовка к настройке основного логирования
                handler
            ) in logging.root.handlers:  # Отказ от предыдущей настройки на логирование
                logging.root.removeHandler(handler)
        except Exception:
            raise

    def completion(
        self, remote_path: str | None = None, e: Exception | None = None
    ) -> None:
        """Завершает работу программы с соответствующим статусом.

        Логирует результат выполнения и вызывает завершение программы
        с кодом 0 (успех) или 1 (ошибка). Также формирует специальное
        сообщение для системы отправки email-уведомлений.

        Args:
            remote_path: (str) Путь к файлу на Яндекс-Диске (для уведомления)
            e: Exception. Прерывание программы.
        """
        handler = MaxLevelHandler()
        max_level = handler.get_highest_level()

        if not self.start_completion_work(remote_path=remote_path):
            max_level = max(max_level, logging.ERROR)
        self.completion_log(max_level, e)
        sys.exit(1 if logging.ERROR <= max_level else 0)

    @staticmethod
    def start_completion_work(remote_path: str | None) -> bool:
        # Специальное сообщение для системы уведомлений
        logger.critical(f"{C.STOP_SERVICE_MESSAGE}{remote_path}")
        message_mail = MessageMail()
        return message_mail.compose_and_send_email()

    def completion_log(self, max_level: int, e: Exception | None = None) -> None:
        """Логирует итоговый результат выполнения задания.

        В зависимости от максимального уровня залогированных ошибок
        формирует соответствующее сообщение в лог.

        Args:
            max_level: (int) Числовой код максимального уровня ошибки
            e: Exception. Прерывание программы.
        """
        name_max_level = logging.getLevelName(max_level)

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

        if e is not None:
            self.log_exception(e)

    @staticmethod
    def log_exception(e: Exception) -> None:
        logger.info("=== Произошла ошибка ===")
        logger.info(f"Тип ошибки: {type(e).__name__}")
        logger.info(f"Сообщение: {str(e)}")

        # Получаем полный traceback
        for handler in logging.root.handlers:
            if handler.level == logging.DEBUG:
                exc_type, exc_value, exc_tb = sys.exc_info()
                tb_list = traceback.format_exception(exc_type, exc_value, exc_tb)

                logger.info("\nПолная трассировка:")
                logger.info("\n".join(exc_value))  # Выводим как единую строку

    def main(self):
        """
        Выполняет:
        1. Настройку системы логирования
        2. Запуск основного процесса создания и загрузки резервных копий

        Логирует все этапы работы и обрабатывает возможные ошибки.
        """

        start_time = time.time()
        remote_path = None
        try:
            self.validate_vars_environments()  # Проверка наличия переменных окружения
        except Exception as e:
            logger.critical({e})
            exit(1)

        try:
            TuneLogger().setup_logging()  # Настройка системы логирования
            remote_path = self.main_program_loop()  # Запуск основного процесса
        except KeyboardInterrupt:
            logger.error(T.canceled_by_user, exc_info=True)
            raise
        except Exception as e:
            self.completion(remote_path=remote_path, e=e)
        else:
            self.completion(remote_path=remote_path, e=None)
        finally:
            logger.info(T.time_run.format(time=f"{time.time() - start_time:.2f}"))

    @staticmethod
    def main_program_loop() -> str:
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
                remote_path = write_file(local_path)
                return remote_path

        except Exception as e:
            raise Exception(e)


if __name__ == "__main__":
    """Точка входа в приложение резервного копирования"""
    try:
        backup_manager = BackupManager()
        backup_manager.main()
        exit(0)
    except Exception:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
