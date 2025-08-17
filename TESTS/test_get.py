
import logging
from SRC.GENERAL.get import get_parameter

def test_get_parameter_missing_levels(caplog):
    d = {}
    caplog.set_level(logging.DEBUG)
    try:
        get_parameter("x", d, level=logging.CRITICAL)
        raised = False
    except KeyError:
        raised = True
    assert raised
    assert get_parameter("x", d, level=logging.ERROR) is None
    assert get_parameter("x", d, level=logging.WARNING) is None
    assert get_parameter("x", d, level=logging.INFO) is None
    assert get_parameter("x", d, level=logging.DEBUG) is None
