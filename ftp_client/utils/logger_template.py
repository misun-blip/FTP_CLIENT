from __future__ import annotations


class LoggerTemplate:
    """Implementation template for the utility owner."""

    def info(self, message: str) -> None:
        raise NotImplementedError

    def error(self, message: str) -> None:
        raise NotImplementedError

