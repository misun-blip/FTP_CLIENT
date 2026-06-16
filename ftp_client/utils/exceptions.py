from __future__ import annotations


class FTPClientError(Exception):
    """Base exception for all project-specific errors."""


class FTPException(FTPClientError):
    """Base exception for FTP client errors."""


class FTPConnectionError(FTPException):
    """Raised when the FTP control or data connection fails."""


class ProtocolError(FTPException):
    """Raised when an FTP response cannot satisfy the expected protocol state."""


class AuthenticationError(FTPException):
    """Raised when FTP authentication fails."""


class TransferError(FTPException):
    """Raised when a file transfer fails."""


class ConfigError(FTPClientError):
    """Raised when configuration loading, validation, or saving fails."""


class ValidationError(FTPClientError):
    """Raised when user input or model data is invalid."""
