import os
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


def _internal_dir() -> Path:
    p = os.getenv("INTERNAL_DIR")
    if p:
        return Path(p)  # постоянная копия из rthook_init.py
    # dev-режим без exe
    return _project_root() / "_internal"


def _project_root() -> Path:
    # Нужен только для dev: найти корень проекта (где лежит SRC)
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "SRC").is_dir():
            return p
    return here.parent


def get_path(rel: str) -> Path:
    return _internal_dir() / rel
