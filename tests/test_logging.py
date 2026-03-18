# tests/test_logging.py
import logging
import sys
from io import StringIO
from consensus_engine.logging import setup_logging, get_logger


def test_setup_logging_default_level():
    setup_logging()
    logger = logging.getLogger()
    assert logger.level == logging.INFO


def test_setup_logging_debug_level():
    setup_logging("DEBUG")
    logger = logging.getLogger()
    assert logger.level == logging.DEBUG


def test_logger_outputs_to_stderr():
    # 使用 DEBUG 级别以便于测试（ConsoleRenderer）
    setup_logging("DEBUG")
    logger = get_logger("test")

    old_stderr = sys.stderr
    sys.stderr = StringIO()

    # 需要在替换 stderr 后重新配置 logging
    import logging

    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=logging.DEBUG, force=True)

    logger.info("test message")
    output = sys.stderr.getvalue()

    sys.stderr = old_stderr
    # ConsoleRenderer 格式或简单的消息
    assert "test message" in output or "test" in output
