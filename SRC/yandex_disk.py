"""
Модуль для работы с. Яндекс. Диском
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

from pathlib import Path
from datetime import date
import time
import re
import requests
import os
import logging

logger = logging.getLogger(__name__)
from tqdm import tqdm

import yadisk
from yadisk.exceptions import PathNotFoundError

from yandex_token import YandexOAuth  # Модуль для работы с OAuth


class YandexDisk:
    """Класс для работы с архивами на Яндекс. Диске"""

    # Стандартные значения для конфигурации
    _ARCHIVE_NAME_FORMAT = "{archive}_{year}_{month:02d}_{day:02d}_{file_num}"
    _ARCHIVE_EXT = ".exe"
    _ARCHIVE_PREFIX = "archive"
    _ARCHIVE_PATH = "disk:/Архивы"

    def __init__(
            self,
            target_date: date | None = date.today(),  # Дата для именования
            archive_prefix: str | None = _ARCHIVE_PREFIX,  # Префикс имени файла архива
            archive_ext: str | None = _ARCHIVE_EXT,  # Расширение файла архива
            archive_path: str | None = _ARCHIVE_PATH,  # Путь на Яндекс. Диске
    ):

        logger.info("Инициализация YandexDisk")

        self.archive_ext = archive_ext
        self.archive_path = archive_path

        # Форматирование шаблона имени с учетом даты
        self.archive_name_format = self._ARCHIVE_NAME_FORMAT.format(
            archive=archive_prefix,
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            file_num="{file_num}",  # Заполнитель для номера
        )

        # Получение токена для API
        try:
            logger.info("Получение токена авторизации")
            yandex_token = YandexOAuth(tokens_file=Path("token.json"), port=12345)
            self.yandex_token = yandex_token.get_token()
            self.disk = yadisk.YaDisk(token=self.yandex_token)
            logger.debug("Токен успешно получен")
        except Exception as e:
            logger.error(f"Ошибка получения токена: {e}")
            raise

    def create_archive_name(self) -> str:
        """
        Генерирует уникальное имя архива на основе существующих файлов
        :return: (str) - Имя архива, сгенерированное по шаблону.
        """
        logger.info("Генерация имени архива")
        # Анализируем существующие архивы на заданную дату и получаем список их номеров
        file_nums = self._get_file_nums()

        # Вычисляем следующий порядковый номер архива на заданную дату
        next_num = max(file_nums) + 1 if file_nums else 1

        # Формируем имя файла архива в соответствии с шаблоном
        archive_name = self.archive_name_format.format(
            file_num=next_num,
        )
        result = f"{archive_name}{self.archive_ext}"
        logger.info(f"Сгенерировано имя архива: {result}")
        return result

    def _get_file_nums(self) -> list[int]:
        """
        Возвращает список номеров файлов в целевой директории на заданную дату
        :return: list[int] - Список номеров файлов архивов на заданную дату
        """
        logger.debug(f"Получение номеров файлов из {self.archive_path}")
        file_nums = []

        try:
            # Получаем список элементов в папке архивов
            for item in self.disk.listdir(self.archive_path):
                # Извлекаем номер из имени файла
                file_num_str = self._extract_file_num(item.name)

                # Пропускаем если не удалось извлечь
                if file_num_str is None:
                    continue

                # Преобразуем в число
                file_nums.append(int(file_num_str))

        # Создание папки для архивов при необходимости
        except PathNotFoundError:  # Папки с архивами не существует
            logger.warning(f"Папка {self.archive_path} не найдена, создаем")
            self.disk.mkdir(self.archive_path)  # Создаём папку с архивами
            logger.info(f"Папка {self.archive_path} создана")
        except Exception as e:
            logger.error(f"Ошибка получения списка файлов: {e}", exc_info=True)
            raise

        logger.debug(f"Найдены номера файлов: {file_nums}")
        return file_nums  # Возвращаем список номеров файлов архивов

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

    def write_archive(self, local_path: str) -> bool:
        """
        Загружает локальный файл на Яндекс. Диск

        :param local_path: Путь к локальному файлу
        :return: Статус операции (True/False)
        """
        logger.info(f"Начало загрузки файла {local_path}")
        # Генерируем уникальное имя архива
        archive_name = self.create_archive_name()

        # Формируем полный путь на Яндекс. Диске
        remote_path = f"{self.archive_path}/{archive_name}"

        try:
            # Загрузка файла
            logger.debug(f"Загрузка {local_path} -> {remote_path}")
            t_start = time.time()
            self.disk.upload(
                local_path,
                remote_path,
                overwrite=False,
                timeout=120,
                chunk_size=1024 * 1024 * 4,
            )
            t_elapsed = time.time() - t_start
            logger.info(
                f"Файл {local_path} успешно загружен в {remote_path} "
                f"за {t_elapsed:.2f} сек."
            )
            return True
        # Обработка специфических ошибок API
        except yadisk.exceptions.UnauthorizedError:
            logger.error("Недействительный токен Яндекс.Диск!", exc_info=True)
            raise PermissionError("Недействительный токен Яндекс.Диск!") from None
        except yadisk.exceptions.PathExistsError:
            logger.error(f"Файл {remote_path} уже существует")
            return False
        except yadisk.exceptions.ForbiddenError:
            logger.error(f"Недостаточно прав для записи в {remote_path}")
            return False
        except Exception as err:
            logger.error(f"Ошибка при загрузке файла: {err}", exc_info=True)
            return False

    def write_archive_fast(self, local_path: str) -> bool:
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
            bool: True, если загрузка прошла успешно, иначе False.

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
            return True

        except Exception as e:
            # Обработка любых исключений при загрузке
            logger.error(f"Ошибка при загрузке файла: {e}", exc_info=True)
            return False

    def write_archive_progress_bar(self, local_path: str) -> bool:
        """
        Загрузка файла на Яндекс. Диск через REST API с отображением прогресса.

        Метод выполняет двухэтапную загрузку:
        1. Получает от Яндекс-Диска временный URL для загрузки.
        2. Загружает файл напрямую по этому URL, отображая прогресс.

        Args:
            local_path (str): Путь к локальному файлу для загрузки.

        Returns:
            bool: True, если загрузка прошла успешно, иначе False.
        """
        logger.info(f"Быстрая загрузка с прогресс-баром: {local_path}")
        upload_url, archive_name = self.get_file_download_URL()
        file_size = os.path.getsize(local_path)
        logger.debug(f"Размер файла: {file_size} байт")
        chunk_size = 1024 * 1024  # 1 MB

        # Начало загрузки с отображением прогресса
        logger.info(f"Начало загрузки файла {archive_name}")
        t0 = time.time()
        try:
            with open(local_path, "rb") as f, tqdm(
                    total=file_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"Загрузка {archive_name}",
                    ncols=80,
            ) as progress:

                def gen():
                    while True:
                        data = f.read(chunk_size)
                        if not data:
                            break
                        progress.update(len(data))
                        yield data

                response = requests.put(upload_url, data=gen())
            response.raise_for_status()

            t1 = time.time()
            logger.info(f"Файл {archive_name} загружен за {t1 - t0:.2f} сек.")
            return True

        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {e}", exc_info=True)
            return False

    def get_file_download_URL(self) -> tuple[str, str] | None:
        """
        Формирование имени файла архива и url пути загрузки файла на Яндекс-Диск
        :return: tuple[str, str] - (url загрузки файла на Яндекс-Диск, сгенерированное имя файла)
                                    или None при неудаче
        """
        # Генерация имени архива и удаленного пути
        archive_name = self.create_archive_name()
        remote_path = f"{self.archive_path}/{archive_name}"
        logger.debug(f"Удаленный путь: {remote_path}")

        # Запрос на получение upload URL
        headers = {"Authorization": f"OAuth {self.yandex_token}"}
        params = {"path": remote_path, "overwrite": "false"}

        url_resp = requests.get(
            "https://cloud-api.yandex.net/v1/disk/resources/upload",
            headers=headers,
            params=params,
        )

        if not url_resp.ok:
            logger.error(f"Ошибка получения upload URL: {url_resp.text}")
            return None

        upload_url = url_resp.json()["href"]
        logger.debug(f"Получен upload URL: {upload_url}")
        return upload_url, archive_name


if __name__ == "__main__":
    # Пример использования
    yandex_disk = YandexDisk()
    print(yandex_disk.write_archive(r"c:\temp\keyboard.log"))
