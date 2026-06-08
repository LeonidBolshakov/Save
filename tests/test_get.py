import logging

import pytest

from src.GENERAL.get import get_parameter


def test_get_parameter_missing_levels(caplog):
    d = {}
    caplog.set_level(logging.DEBUG)
    with pytest.raises(KeyError):
        get_parameter("x", d, level=logging.CRITICAL)

    assert get_parameter("x", d, level=logging.ERROR) is None
    assert get_parameter("x", d, level=logging.WARNING) is None
    assert get_parameter("x", d, level=logging.INFO) is None
    assert get_parameter("x", d, level=logging.NOTSET) is None
