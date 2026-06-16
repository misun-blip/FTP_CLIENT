from __future__ import annotations

import logging
from pathlib import Path
from typing import TextIO


DEFAULT_LOG_FORMAT = "[%(levelname)s] %(message)s"


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level

    normalized = level.upper()
    if normalized not in logging._nameToLevel:
        raise ValueError(f"unsupported log level: {level}")
    return logging._nameToLevel[normalized]


def get_logger(
    name: str = "ftp_client",
    *,
    level: int | str = logging.INFO,
    log_file: str | Path | None = None,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Return a configured logger for application modules."""
    logger = logging.getLogger(name)
    logger.setLevel(_resolve_level(level))
    logger.propagate = False

    if not logger.handlers:
        logger.addHandler(_build_stream_handler(stream))

    if log_file is not None:
        _ensure_file_handler(logger, Path(log_file))

    return logger


def _build_stream_handler(stream: TextIO | None = None) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    return handler


def _ensure_file_handler(logger: logging.Logger, log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    target = str(log_file.resolve())

    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == target:
            return

    file_handler = logging.FileHandler(target, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(DEFAULT_LOG_FORMAT))
    logger.addHandler(file_handler)


class AppLogger:
    """Small adapter matching the shared LoggerProtocol."""

    def __init__(
        self,
        name: str = "ftp_client",
        *,
        level: int | str = logging.INFO,
        log_file: str | Path | None = None,
        stream: TextIO | None = None,
    ) -> None:
        self._logger = get_logger(
            name,
            level=level,
            log_file=log_file,
            stream=stream,
        )

    def info(self, message: str) -> None:
        self._logger.info(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


_default_logger = AppLogger()


def info(message: str) -> None:
    """Write an info message through the shared application logger."""
    _default_logger.info(message)


def error(message: str) -> None:
    """Write an error message through the shared application logger."""
    _default_logger.error(message)


def log_protocol(command: str, response: str) -> None:
    """Record an FTP command/response pair for protocol troubleshooting."""
    get_logger("ftp_client.protocol").info("FTP %s -> %s", command, response)
