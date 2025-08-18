import sys
from pathlib import Path
from typing import Any
import logging
from logging import getLogger

logger = getLogger(__name__)

from SRC.GENERAL.textmessage import TextMessage as T


def get_parameter(
    parameter: str, parameters_dict: dict[str, Any], level: int = logging.CRITICAL
) -> Any:
    try:
        value = parameters_dict[parameter]
        return value
    except KeyError as e:
        match level:
            case logging.CRITICAL:
                logger.critical(T.error_parameter_archiver.format(param=parameter))
                raise KeyError from e
            case logging.DEBUG:
                pass
            case _:
                logger.info(T.error_parameter_archiver.format(param=parameter))
    return None


def _runtime_base() -> Path:
    if getattr(sys, "frozen", False):
        mp = getattr(sys, "_MEIPASS", None)  # onefile → временная папка с ресурсами
        return Path(mp) if mp else Path(sys.executable).parent  # onedir
    # dev: корень проекта (ищем каталог с SRC)
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "SRC").is_dir():
            return p
    return here.parent


def get_path(rel: str) -> Path:
    return _runtime_base() / rel
