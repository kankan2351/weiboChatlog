import io
import logging

from chatbot.utils.logger import get_logger, log_error, log_warning, log_info


def test_get_logger_returns_singleton():
    logger_a = get_logger("test_logger")
    logger_b = get_logger("test_logger")
    assert logger_a is logger_b
    assert logger_a.level == logging.INFO
    assert logger_a.handlers, "Logger should have at least one handler"


def test_logging_helpers_emit_messages():
    test_logger = get_logger("chatbot")
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    try:
        log_info("info message")
        log_warning("warn message")
        log_error(Exception("boom"), context="ctx")
    finally:
        test_logger.removeHandler(handler)

    output = stream.getvalue()
    assert "info message" in output
    assert "warn message" in output
    assert "ctx" in output
