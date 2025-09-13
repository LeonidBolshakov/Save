import subprocess
from pathlib import Path
import tempfile
import logging

from SRC.ARCHIVES.search_programme_abc import SearchProgramme

from SRC.GENERAL.textmessage import TextMessage as T

logger = logging.getLogger(__name__)


class SearchProgramme7Z(SearchProgramme):

    def test_programme_execution(self, path: str) -> bool:
        """
        Программа выполняет передаваемую в параметре программу на минимальных данных.
        Если программа выполниться без прерываний и вернёт код возврата 0, то всё ОК.

        :param path: (str) Полный путь на выполняемую программу.

        :return:True, если всё ОК, иначе False
        """

        # Создаём архив 7z и анализируем код результата
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                test_archive = Path(tmpdir) / "test.exe"  # Архив
                test_file = Path(tmpdir) / "test.txt"  # Архивируемый файл
                test_file.write_text("Test", encoding="utf-8")

                result = subprocess.run(  # Архивация
                    [path, "a", "-sfx", str(test_archive), str(test_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if result.returncode != 0:  # Анализ кода возврата
                    logger.debug(
                        T.error_run_programme.format(path=path, e=result.stderr)
                    )
                return result.returncode == 0
            except Exception as e:  # Аварийное завершение архиватора
                logger.debug(T.error_run_programme.format(path=path, e=e))
                return False
