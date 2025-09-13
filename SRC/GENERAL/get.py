from typing import Any
import logging
from logging import getLogger

from SRC.GENERAL.textmessage import TextMessage as T

logger = getLogger(__name__)


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
