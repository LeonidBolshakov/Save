import sys
import time
import traceback
from typing import Any
from abc import ABC, abstractmethod
from tempfile import TemporaryDirectory
import logging

logger = logging.getLogger(__name__)

from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.MAIL.messagemail import MessageMail
from SRC.GENERAL.environment_variables import EnvironmentVariables
from SRC.GENERAL.manager_write_file import write_file
from SRC.LOGGING.tunelogger import TuneLogger
from SRC.GENERAL.get import get_parameter
from SRC.GENERAL.constants import Constants as C
from SRC.GENERAL.textmessage import TextMessage as T


class BackupManager(ABC):
    """Класс для управления процессом резервного копирования данных.

    Обеспечивает:
    - Создание локального архива с данными
    - Загрузку локального архива на Яндекс-Диск
    - Обработку ошибок и логирование процесса
    - Отправку служебного e-mail, информирующего о статусе выполнения задания.

    В дочернем классе требуется переопределить метод:
    get_parameters_dict

    Прерывания:
    1. Прекращение работы программы с клавиатуры.
    2. Обработка всех прерываний внутренних программ.
    """

    def __init__(self):
        # Доступ к переменным окружения
        self.variables = EnvironmentVariables()

    def main(self):
        """
        Основная точка входа в класс.

        Выполняет:
        1. Настройку системы логирования
        2. Запуск основного процесса создания и загрузки резервных копий

        Логирует все этапы работы и обрабатывает возможные ошибки.
        """

        start_time = time.time()
        remote_path = None

        self._create_temp_logging()
        logging.raiseExceptions = False  # запрет вывода трассировки

        try:
            self.variables.validate_vars()  # Проверка наличия необходимых переменных окружения
        except Exception as e:
            logger.critical(str(e))
            exit(1)

        logging.raiseExceptions = True  # Отмена запрета вывода трассировки

        try:
            TuneLogger().setup_logging()  # Настройка системы логирования
        except Exception as e:
            print(f"Ошибка при настройке системы логирования {e}")

        try:
            remote_path = self._main_program_loop()  # Запуск основного процесса
        except KeyboardInterrupt:
            logger.error(T.canceled_by_user)
            self._completion(remote_path=remote_path, e=None)
        except Exception as e:
            self._completion(remote_path=remote_path, e=e)
        else:
            self._completion(remote_path=remote_path, e=None)
        finally:
            executed_time = time.time() - start_time
            logger.info(T.time_run.format(time=f"{executed_time:.2f}"))

    def _main_program_loop(self) -> str | None:
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
            # Используем with для автоматической очистки временных файлов
            with TemporaryDirectory() as temp_dir:
                try:
                    parameters_dict[C.PAR_ARCHIVE_DIR] = temp_dir
                except Exception as e:
                    logger.critical(
                        T.error_parameter_archiver.format(param=C.PAR_ARCHIVE_DIR)
                    )
                    raise KeyError from e

                Archiver = get_parameter(
                    C.PAR___ARCHIVER, parameters_dict=parameters_dict
                )  # Получаем класса архиватора
                archiver = Archiver()
                if archive_path := archiver.create_archive(
                    parameters_dict=parameters_dict
                ):  # Создаём локальный архив
                    remote_path = write_file(
                        archive_path
                    )  # Записываем локальный архив в облако
                    return remote_path
                return None
        except Exception as e:
            raise RuntimeError(e) from e

    @abstractmethod
    def get_parameters_dict(self) -> dict[str, Any]:
        """
        Функция формирует и возвращает словарь параметров
        :return: Словарь параметров
        Обязательные ключи словаря:
            Archiver: - Дочерний класс архиватора. Например, Archiver7z
            SearchProgramme: - Дочерний класс для поиска программы. Например, SearchProgramme7Z
            archive_extension: str - Расширение архива. Например, '.exe'
            archiver_name: str - Шаблон имени программы
            archiver_standard_program_paths: list[str] - Стандартные пути программы (Опционально)
            compression_level: int Уровень сжатия  (опционально) [0, 9]. 0- без сжатия, 9 - ультра сжатие
            config_file_path: str - Путь на файл конфигурации с путями программ
            list_archive_file_paths: str - Путь на файл, содержащий архивируемые файлы
            local_archive_name: str - Имя локального архива
            password: str - Пароль (опционально)
        """
        pass

    def _create_temp_logging(self) -> None:
        """Делает настройки временного логирования, применимого при выполнении одного метода"""
        log_file_path = self.variables.get_var(C.ENV_LOG_FILE_PATH, C.LOG_FILE_PATH_DEF)

        logging.basicConfig(
            level=logging.INFO,
            format=C.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file_path),
            ],
        )  # Настройка действует только до настройки основного логирования

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
        max_level = MaxLevelHandler().get_highest_level()
        if e is not None:
            max_level = max(max_level, logging.ERROR)

        if not self._start_finishing_work(remote_path=remote_path):
            max_level = max(
                max_level, logging.ERROR
            )  # Если письмо не отправлено - уровень сообщений не ниже ERROR

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
        # с сохранёнными в облаке файлами.
        # Эта информация будет использованы при формировании текста e-mail, она не будет выведена в логи

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
                logger.info(
                    T.task_successfully.format(max_level_name=max_level_name.upper())
                )
            case logging.WARNING:
                logger.warning(
                    T.task_warnings.format(max_level_name=max_level_name.upper())
                )
            case logging.ERROR:
                logger.error(T.task_error.format(max_level_name=max_level_name.upper()))
            case logging.CRITICAL:
                logger.critical(
                    T.task_error.format(max_level_name=max_level_name.upper())
                )

        if e is not None:
            self._log_exception(e)

    @staticmethod
    def _log_exception(e: Exception) -> None:
        """
        Логирование того факта, что сохранение данных завершилась исключением.
        Выполняется только для логирования с уровнем DEBUG
        :param e: (Exception) исключение, вызвавшее прекращение сохранения данных.
        :return: None
        """
        logger.info(r"\n=== Произошла ошибка ===")
        logger.info(f"Сообщение: {e}")

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
