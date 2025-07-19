"""
Модуль для работы с. Яндекс-Диском
Обеспечивает загрузку архивов с автоматическим именованием
и проверкой существующих файлов.

Основной класс:
- YandexDisk: Управление загрузкой архивов

Особенности:
- Автоматическая генерация имен файлов по шаблону
- Проверка валидности токена перед загрузкой
- Обработка специфических ошибок API
- Автоматическое создание папки для архивов
- Подробное логирование операций
"""

from datetime import date
import time
import re
import requests
import logging

logger = logging.getLogger(__name__)

import yadisk
from yadisk.exceptions import PathNotFoundError, PathExistsError

from SRC.YADISK.yandex_token import YandexOAuth  # Модуль для работы с OAuth
from SRC.GENERAL.constant import Constant as C


class YandexDisk:
    """Класс для работы с архивами на Яндекс. Диске"""

    def __init__(
        self,
        target_date: date = date.today(),  # Дата для именования
        archive_prefix: str = C.REMOTE_ARCHIVE_PREFIX,  # Префикс имени файла архива
        archive_ext: str = C.ARCHIVE_SUFFIX,  # Расширение файла архива
        archive_path: str = C.REMOTE_ARCHIVE_PATH,  # Каталог архивов на Яндекс-Диске
    ):
        logger.info("Инициализация YandexDisk")

        self.target_date = target_date
        self.archive_prefix = archive_prefix
        self.archive_ext = archive_ext
        self.archive_path: str = archive_path if archive_path else C.REMOTE_ARCHIVE_PATH
        self.yandex_token: str | None = None
        self.disk = yadisk.YaDisk()

        self.archive_name_format = self.get_archive_name_format()
        self.get_token_for_API()

    def get_archive_name_format(self):
        return C.GENERAL_REMOTE_ARCHIVE_FORMAT.format(
            archive=self.archive_prefix,
            year=self.target_date.year,
            month=self.target_date.month,
            day=self.target_date.day,
            file_num="{file_num}",  # Заполнитель для номера
        )

    def get_token_for_API(self):
        # Получение токена для API
        try:
            logger.info("Получение токена авторизации")
            yandex_token = YandexOAuth(port=12345)
            self.yandex_token = yandex_token.get_token()
            if not self.yandex_token:
                error_msg = "Нет доступа к Яндекс-Диск. Токен недействителен."
                logger.critical(error_msg)
                raise PermissionError(error_msg)
            self.disk.token = self.yandex_token
            logger.debug("Токен успешно получен")
        except Exception as e:
            error_msg = f"Ошибка получения токена: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def remote_archive_name(self) -> str:
        """
        Генерирует уникальное имя архива на основе существующих файлов
        :return: (str) - Имя архива, сгенерированное по шаблону.
        """
        logger.info("Генерация имени архива")
        # Вычисляем следующий порядковый номер архива на заданную дату
        next_num = max(self._get_file_nums(), default=0) + 1

        # Формируем имя файла архива в соответствии с шаблоном
        return f"{self.archive_name_format.format(file_num=next_num)}{self.archive_ext}"

    def _get_file_nums(self) -> list[int]:
        """
        Возвращает список номеров файлов на заданную дату в целевой директории
        :return: list[int] - Список номеров файлов архивов на заданную дату
        """
        logger.debug(f"Получение номеров файлов из {self.archive_path}")

        try:
            # Получаем список элементов в папке архивов
            file_nums = self._list_file_nums()
            logger.debug(f"Найдены номера файлов: {file_nums}")
            return file_nums  # Возвращаем список номеров файлов архивов
        # Создание папки для архивов при необходимости
        except PathNotFoundError:  # Папки с архивами не существует
            logger.info(f"Папка {self.archive_path} не найдена, создаем")
            self.disk.mkdir(self.archive_path)  # Создаём папку с архивами
            logger.info(f"Папка {self.archive_path} создана")
            return []
        except Exception as e:
            error_msg = f"Ошибка получения списка файлов: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _list_file_nums(self) -> list[int]:
        file_nums = []
        for item in self.disk.listdir(self.archive_path):
            # Извлекаем номер из имени файла
            if item.name is None:
                logger.info("Обнаружен None-элемент в списке файлов Яндекс-Диска.")
                continue
            file_num_str = self._extract_file_num(item.name)

            # Пропускаем если не удалось извлечь
            if file_num_str is None:
                continue

            # Преобразуем в число
            file_nums.append(int(file_num_str))
        return file_nums

    def _extract_file_num(self, filename: str) -> int | None:
        """
        Извлекает номер файла из имени файла с помощью регулярного выражения

        :param: filename: (str) - имя файла
        Returns:
            int: номер файла
            None: если имя не соответствует шаблону
        """
        re_archive_name = self._get_archive_pattern_for_date()
        if match := re.match(re_archive_name, filename):
            return int(match.group("file_num"))
        return None

    def _get_archive_pattern_for_date(self) -> re.Pattern:
        """
        Генерирует регулярное выражение для поиска файлов текущего формата
        с учетом даты и префикса
        :return: re. Pattern Сгенерированное регулярное выражение
        """
        # Формируем фиксированный префикс из общего формата
        prefix = self.archive_name_format.format(
            file_num="",  # Убираем часть с номером файла
        )

        # Экранируем спецсимволы для regex
        escaped_prefix = re.escape(prefix)
        escaped_ext = re.escape(self.archive_ext)

        # Собираем полное регулярное выражение
        return re.compile(
            rf"^{escaped_prefix}(?P<file_num>\d+){escaped_ext}$",
            # (?P<file_num>\d+) - группа file_num для номера файла за дату
            re.IGNORECASE,  # Регистронезависимый поиск
        )

    def write_file(self, local_path: str) -> bool:
        """
        Загружает локальный файл на Яндекс. Диск

        :param local_path: Путь к локальному файлу
        :return: Статус операции (True/False)
        """
        logger.info(f"Начало загрузки файла {local_path}")

        # Формируем полный путь на Яндекс. Диске
        remote_path = f"{self.remote_archive_name}/{self.remote_archive_name()}"

        try:
            # Загрузка файла
            self._upload_file(local_path, remote_path)
            return True
        # Обработка специфических ошибок API
        except yadisk.exceptions.UnauthorizedError:
            error_msg = "Недействительный токен Яндекс.Диск!"
            logger.critical(error_msg, exc_info=True)
            raise PermissionError(error_msg) from None
        except yadisk.exceptions.PathExistsError:
            error_msg = f"Файл {remote_path} уже существует"
            logger.error(error_msg, exc_info=True)
            raise PathExistsError(error_msg) from None
        except yadisk.exceptions.ForbiddenError:
            error_msg = f"Недостаточно прав для записи в {remote_path}"
            logger.critical(error_msg, exc_info=True)
            raise PermissionError(error_msg) from None
        except Exception as err:
            error_msg = f"Ошибка при загрузке файла: {err}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from None

    def _upload_file(self, local_path: str, remote_path: str) -> None:
        """Выполняет загрузку файла и логирует время."""
        logger.debug(f"Загрузка {local_path} -> {remote_path}")
        t_start = time.time()
        self.disk.upload(
            local_path,
            remote_path,
            overwrite=False,
            timeout=120,
            chunk_size=4 * 1024 * 1024,
        )
        logger.info(f"Файл загружен за {time.time() - t_start:.2f} сек.")

    def write_file_fast(self, local_path: str) -> str | None:
        """
        Быстрая загрузка файла на Яндекс-Диск через прямой REST API.

        Метод использует двухэтапную загрузку:
        1. Получает уникальный URL для загрузки от Яндекс-Диска (через API).
        2. Загружает файл напрямую по этому URL с помощью HTTP PUT.

        Этот способ обеспечивает максимальную производительность, сопоставимую
        с загрузкой через веб-интерфейс, в отличие от стандартного метода через yadisk.

        Args:
            local_path (str): Путь к локальному файлу, который нужно загрузить.

        Returns:
            bool: путь на архив на целевом (облачном) диске, если загрузка прошла успешно, иначе None.

        Raises:
            Непосредственно не выбрасывает исключения наружу, но печатает ошибки,
            возникшие при получении URL или при самой загрузке файла.
        """
        logger.info(f"Быстрая загрузка файла {local_path}")
        upload_url, remote_path = self.get_file_download_URL()
        try:
            # Открываем локальный файл в бинарном режиме
            with open(local_path, "rb") as f:
                # Шаг 2: загружаем файл напрямую на полученный URL через HTTP PUT
                logger.info(f"Начало быстрой загрузки файла {local_path}")
                response = requests.put(upload_url, data=f)

            # Проверка на успешную загрузку (ошибки вызовут исключение)
            response.raise_for_status()
            logger.info(f"Файл {local_path} успешно загружен в {remote_path}")
            return remote_path

        except Exception as e:
            # Обработка любых исключений при загрузке
            logger.error(f"Ошибка при загрузке файла: {e}", exc_info=True)
            return None

    def get_file_download_URL(self) -> tuple[str, str]:
        """
        Формирование имени файла архива и url пути загрузки файла на Яндекс-Диск
        :return: tuple[str, str] - (url загрузки файла на Яндекс-Диск, сгенерированное имя файла)
                                    или None при невозможности сгенерировать имя
        """
        # Генерация имени архива и удаленного пути
        archive_name = self.remote_archive_name()
        remote_path = f"{self.archive_path}/{archive_name}"
        logger.debug(f"Путь на архив в облаке: {remote_path}")
        upload_url = self._get_upload_url(remote_path)

        logger.debug(f"Получен upload URL: {upload_url}")
        return upload_url, archive_name

    def _get_upload_url(self, remote_path: str) -> str:
        """Выполняет запрос к API для получения URL загрузки."""
        response = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources/upload",
            headers={"Authorization": f"OAuth {self.yandex_token}"},
            params={"path": remote_path, "overwrite": "false"},
        )
        if not response.ok:
            raise RuntimeError(f"Ошибка получения upload URL: {response.text}")
        return response.json()["href"]


if __name__ == "__main__":
    # Пример использования
    yandex_disk = YandexDisk()
    print(yandex_disk.write_file(r"yandex_disk.py"))
