from __future__ import annotations

import io

from ftp_client.interfaces import LoggerProtocol
from ftp_client.utils.logger import AppLogger, get_logger, log_protocol


def test_app_logger_matches_logger_protocol() -> None:
    logger: LoggerProtocol = AppLogger(name="test.member6.protocol", stream=io.StringIO())

    logger.info("ready")
    logger.error("failed")


def test_app_logger_writes_info_and_error_messages() -> None:
    stream = io.StringIO()
    logger = AppLogger(name="test.member6.messages", stream=stream)

    logger.info("ready")
    logger.error("failed")

    output = stream.getvalue()
    assert "[INFO] ready" in output
    assert "[ERROR] failed" in output


def test_get_logger_does_not_add_duplicate_handlers() -> None:
    stream = io.StringIO()
    logger = get_logger("test.member6.duplicates", stream=stream)
    initial_handler_count = len(logger.handlers)

    same_logger = get_logger("test.member6.duplicates", stream=stream)

    assert same_logger is logger
    assert len(same_logger.handlers) == initial_handler_count


def test_get_logger_can_write_to_file(tmp_path) -> None:
    log_file = tmp_path / "logs" / "client.log"
    logger = get_logger("test.member6.file", log_file=log_file)

    logger.info("persisted")

    assert "persisted" in log_file.read_text(encoding="utf-8")


def test_log_protocol_records_command_and_response() -> None:
    stream = io.StringIO()
    get_logger("ftp_client.protocol", stream=stream)

    log_protocol("PWD", "257 /")

    assert "FTP PWD -> 257 /" in stream.getvalue()
