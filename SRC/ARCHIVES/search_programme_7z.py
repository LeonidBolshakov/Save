import subprocess
from pathlib import Path
import tempfile
import logging

from SRC.ARCHIVES.search_programme_abc import SearchProgramme

logger = logging.getLogger(__name__)

from SRC.GENERAL.textmessage import TextMessage as T


class SearchProgramme7Z(SearchProgramme):

    def _test_programme_execution(self, path: str) -> bool:
        """Тестирует выполнение программы."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                test_archive = Path(tmpdir) / "test.exe"
                test_file = Path(tmpdir) / "test.txt"
                test_file.write_text("Test", encoding="utf-8")

                result = subprocess.run(
                    [path, "a", "-sfx", str(test_archive), str(test_file)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                if result.returncode != 0:
                    logger.debug(
                        T.error_run_programme.format(path=path, e=result.stderr)
                    )
                return result.returncode == 0
            except Exception as e:
                logger.debug(T.error_run_programme_except.format(path=path, e=e))
                return False
