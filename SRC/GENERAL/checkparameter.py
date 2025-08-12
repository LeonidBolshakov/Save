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
    except KeyError as e:
        if level == logging.CRITICAL:
            logger.critical(T.error_parameter_archiver.format(param=parameter))
            raise KeyError from e
        else:
            logger.warning(T.error_parameter_archiver.format(param=parameter))
            return None
    else:
        return value
