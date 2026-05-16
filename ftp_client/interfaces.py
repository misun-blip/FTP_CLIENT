from __future__ import annotations

from typing import Protocol

from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import TransferTask


class FTPClientProtocol(Protocol):
    """Protocol-layer contract provided by the protocol owner."""

    def connect(self, host: str, port: int, timeout: int = 10) -> None: ...

    def login(self, username: str, password: str) -> bool: ...

    def list_dir(self, path: str | None = None) -> list[RemoteFile]: ...

    def close(self) -> None: ...


class DownloaderProtocol(Protocol):
    """Download-layer contract provided by the download owner."""

    def download(self, remote_path: str, local_path: str) -> TransferTask: ...

    def resume_download(self, remote_path: str, local_path: str) -> TransferTask: ...


class UploaderProtocol(Protocol):
    """Upload-layer contract provided by the upload owner."""

    def upload(self, local_path: str, remote_path: str) -> TransferTask: ...

    def resume_upload(self, local_path: str, remote_path: str) -> TransferTask: ...


class LoggerProtocol(Protocol):
    """Shared logging contract provided by the utility owner."""

    def info(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...


class MainWindowProtocol(Protocol):
    """GUI entry contract provided by the GUI owner."""

    def show(self) -> None: ...

