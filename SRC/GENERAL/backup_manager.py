import sys
import time
import traceback
from abc import ABC, abstractmethod
from tempfile import TemporaryDirectory
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.MAIL.messagemail import MessageMail
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.manager_write_file import write_file
from SRC.LOGGING.tunelogger import TuneLogger
from SRC.ARCHIVES.archiver7z import Archiver7z
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class BackupManager(ABC):
    """Класс для управления процессом резервного копирования данных.

    Обеспечивает:
    - Создание локального архива с данными
    - Загрузку архива на Яндекс-Диск
    - Обработку ошибок и логирование процесса
    - Отправку служебного e-mail, информирующего о статусе выполнения задания.

    Прерывания:
    1. Прекращение работы программы с клавиатуры.
    2. Обработка всех прерываний внутренних программ.
    """

    def __init__(self):
        self.variables = EnvironmentVariables()

    def main(self):
        """
        Выполняет:
        1. Настройку системы логирования
        2. Запуск основного процесса создания и загрузки резервных копий

        Логирует все этапы работы и обрабатывает возможные ошибки.
        """

        start_time = time.time()
        remote_path = None

        self._create_temp_logging()
        try:
            self.variables.validate_vars()  # Проверка наличия необходимых переменных окружения
        except Exception as e:
            logger.critical(str(e))
            exit(1)
        self._remove_temp_loging()

        try:
            TuneLogger().setup_logging()  # Настройка системы логирования
            remote_path = self._main_program_loop()  # Запуск основного процесса
        except KeyboardInterrupt:
            logger.error(T.canceled_by_user, exc_info=True)
            raise
        except Exception as e:
            self._completion(remote_path=remote_path, e=e)
        else:
            self._completion(remote_path=remote_path, e=None)
        finally:
            logger.info(T.time_run.format(time=f"{time.time() - start_time:.2f}"))

    def _main_program_loop(self) -> str:
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

        parameters_dict = self.get_parameters_dict()
        try:
            # Используем TemporaryDirectory для автоматической очистки временных файлов
            with TemporaryDirectory() as temp_dir:
                parameters_dict["archive_catalog"] = temp_dir
                archive_path: str = str(
                    Path(
                        temp_dir,
                        parameters_dict["local_archive_name"],
                    )
                )
                parameters_dict["archive_path"] = archive_path
                archiver = Archiver7z(parameter_dict=parameters_dict)
                archiver.create_archive()
                remote_path = write_file(archive_path)
                return remote_path

        except Exception as e:
            raise RuntimeError(e)

    @abstractmethod
    def get_parameters_dict(self) -> dict:
        pass

    def _create_temp_logging(self) -> None:
        """Делает настройки временного логирования"""
        log_file_name = self.variables.get_var(C.ENV_LOG_FILE_NAME, C.LOG_FILE_NAME)

        logging.raiseExceptions = False  # запрет вывода трассировки
        logging.basicConfig(
            level=logging.INFO,
            format=C.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file_name),
            ],
        )  # Настройка логирования только для использования до настройки основного логирования

    @staticmethod
    def _remove_temp_loging() -> None:
        """Удаление настроек временного логирования"""
        logging.raiseExceptions = True
        logger_root = logging.getLogger()
        for handler in logger_root.handlers[:]:
            logger_root.removeHandler(
                handler
            )  # Отказ от предыдущей настройки логирования

    def _completion(
        self, remote_path: str | None = None, e: Exception | None = None
    ) -> None:
        """Завершает работу программы исходя их максимального уровня лога сообщений.

        Логирует результат выполнения и вызывает завершение программы
        с кодом 0 (успех) или 1 (ошибка). Также формирует служебное
        сообщение и отправляет его по email-уведомлений.

        Args:
            remote_path: (str). Путь к файлу на Яндекс-Диске (для уведомления)
            e: Exception. Прерывание программы.
        """
        if e is not None:
            logger.error("")
        max_level = MaxLevelHandler().get_highest_level()

        if not self._start_finishing_work(
            remote_path=remote_path
        ):  # Если письмо не отправлено
            max_level = max(max_level, logging.ERROR)  # уровень сообщений не ниже ERROR

        self._log_end_messages(max_level, e)

        sys.exit(1 if logging.ERROR <= max_level else 0)

    @staticmethod
    def _start_finishing_work(remote_path: str | None) -> bool:
        """
        Инициация завершающего действия после завершения копирования -
        формирование и отправка служебного e-mail.
        :param remote_path: (str). Путь на архив, с сохранёнными в облаке файлами
        :return: True если служебное сообщение удалось отправить, False в противном случае.
        """
        logger.critical(
            f"{C.STOP_SERVICE_MESSAGE}{remote_path}"
        )  # Отправка в систему логирования информации о завершении работы и пути на архив,
        # с сохранёнными в облаке файлами. Эта информация будет использованы при формировании текста e-mail.
        # Эта информация не будет выведена в логи.

        return MessageMail().compose_and_send_email()  # Формирование и отправка e-mail

    def _log_end_messages(self, max_level: int, e: Exception | None = None) -> None:
        """Логирует результат выполнения задания.

        В зависимости от максимального уровня залогированных ошибок
        формирует соответствующее сообщение в лог.

        Args:
            max_level: (int) Числовой код максимального уровня ошибки
            e: Exception. Прерывание программы.
        """
        max_level_name = logging.getLevelName(max_level)

        match max_level:
            case logging.NOTSET | logging.DEBUG | logging.INFO:
                logger.info(T.task_successfully)
            case logging.WARNING:
                logger.warning(
                    T.task_warnings.format(name_max_level=max_level_name.upper())
                )
            case logging.ERROR:
                logger.error(T.task_error.format(name_max_level=max_level_name.upper()))
            case logging.CRITICAL:
                logger.critical(
                    T.task_error.format(name_max_level=max_level_name.upper())
                )

        if e is not None:
            self._log_exception(e)

    @staticmethod
    def _log_exception(e: Exception) -> None:
        """
        Логирование того факта, что сохранение данных завершилась исключением.
        :param e: (Exception) исключение, вызвавшее прекращение сохранения данных.
        :return: None
        """
        logger.info(r"\n=== Произошла ошибка ===")
        logger.info(f"Сообщение: {str(e)}")

        # Для логирования уровня DEBUG выводим полный traceback
        logger_root = logging.getLogger()
        tb_text = "".join(traceback.format_exception(type(e), e, e.__traceback__))

        for handler in logger_root.handlers[:]:
            if handler.level == logging.DEBUG:
                record = logger_root.makeRecord(
                    name=logger_root.name,
                    level=logging.DEBUG,
                    fn="",
                    lno=0,
                    msg=f"%s",
                    args=(tb_text,),
                    exc_info=None,
                )
                handler.handle(record)
