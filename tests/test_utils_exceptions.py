from __future__ import annotations

from ftp_client.utils.exceptions import (
    AuthenticationError,
    ConfigError,
    FTPClientError,
    FTPConnectionError,
    FTPException,
    ProtocolError,
    TransferError,
    ValidationError,
)


def test_exception_hierarchy_groups_project_errors() -> None:
    assert issubclass(FTPException, FTPClientError)
    assert issubclass(FTPConnectionError, FTPException)
    assert issubclass(ProtocolError, FTPException)
    assert issubclass(AuthenticationError, FTPException)
    assert issubclass(TransferError, FTPException)
    assert issubclass(ConfigError, FTPClientError)
    assert issubclass(ValidationError, FTPClientError)
