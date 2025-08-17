
import io, logging
from SRC.LOGGING.customstreamhandler import CustomStreamHandler
from SRC.LOGGING.customrotatingfilehandler import CustomRotatingFileHandler
from SRC.LOGGING.maxlevelhandler import MaxLevelHandler
from SRC.GENERAL.constants import Constants as C
def test_custom_stream_handler_filters_and_writes():
    stream = io.StringIO()
    h = CustomStreamHandler(stream=stream)
    logger = logging.getLogger("t1")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(h)
    logger.info("normal message")
    logger.info(h.email_send_trigger)
    out = stream.getvalue()
    assert "normal message" in out
    assert h.email_send_trigger not in out
def test_custom_rotating_file_handler_write_and_filter(tmp_path):
    log_file = tmp_path / "app.log"
    h = CustomRotatingFileHandler(str(log_file), maxBytes=1024, backupCount=1, encoding="utf-8")
    logger = logging.getLogger("t2")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(h)
    logger.info("keep this")
    logger.info(h.email_send_trigger)
    h.flush()
    data = log_file.read_text(encoding="utf-8")
    assert "keep this" in data
    assert h.email_send_trigger not in data
def test_maxlevelhandler_state_and_trigger():
    MaxLevelHandler.highest_level = logging.NOTSET
    MaxLevelHandler.last_time = 0.0
    MaxLevelHandler.remote_archive_path = ""
    mh = MaxLevelHandler()
    logger = logging.getLogger("t3")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(mh)
    logger.debug("dbg")
    logger.warning("wrn")
    assert MaxLevelHandler.highest_level == logging.WARNING
    trigger_msg = f"{C.ARCHIVING_END_TRIGGER} {C.LINK_REMOTE_ARCHIVE}/disk/file.7z "
    logger.info(trigger_msg)
    assert mh.permanent_lock is True
    assert MaxLevelHandler.remote_archive_path.endswith("/disk/file.7z")
    logger.error("err")
    assert MaxLevelHandler.highest_level == logging.WARNING
