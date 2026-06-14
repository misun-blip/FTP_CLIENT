from __future__ import annotations


class FTPException(Exception):
    """Base exception for FTP client errors."""


class AuthenticationError(FTPException):
    """Raised when FTP authentication fails."""


class TransferError(FTPException):
    """Raised when a file transfer fails."""
