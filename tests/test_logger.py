import logging
import sys

from utils.logger import get_logger


def test_get_logger_returns_logger():
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)


def test_get_logger_outputs_to_stdout():
    logger = get_logger("test_stdout")
    assert any(
        isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
        for h in logger.handlers
    )


def test_get_logger_level_is_info():
    logger = get_logger("test_level")
    assert logger.level == logging.INFO


def test_get_logger_same_name_returns_same_instance():
    a = get_logger("test_singleton")
    b = get_logger("test_singleton")
    assert a is b


def test_get_logger_does_not_duplicate_handlers():
    get_logger("test_dedup")
    get_logger("test_dedup")
    logger = get_logger("test_dedup")
    assert len(logger.handlers) == 1
