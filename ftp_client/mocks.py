from __future__ import annotations

from pathlib import Path

from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import TransferDirection, TransferStatus, TransferTask
from ftp_client.transfer.download_resume import compute_resume_position


class MockFTPClient:
    """Minimal mock for integration before the real protocol layer is ready."""

    def __init__(self) -> None:
        self.connected = False
        self.logged_in = False

    def connect(self, host: str, port: int, timeout: int = 10) -> None:
        self.connected = True

    def login(self, username: str, password: str) -> bool:
        if not self.connected:
            raise RuntimeError("not connected")
        self.logged_in = True
        return True

    def list_dir(self, path: str | None = None) -> list[RemoteFile]:
        if not self.logged_in:
            raise RuntimeError("not logged in")
        return [
            RemoteFile(
                name="docs",
                path="/docs",
                size=0,
                is_dir=True,
                modified_time="2026-05-16 10:00:00",
            ),
            RemoteFile(
                name="demo.txt",
                path="/demo.txt",
                size=1024,
                is_dir=False,
                modified_time="2026-05-16 10:30:00",
            ),
        ]

    def close(self) -> None:
        self.connected = False
        self.logged_in = False


class MockDownloader:
    """Mock downloader for GUI integration before a real FTP server is available."""

    def __init__(self, ftp_client: MockFTPClient | None = None) -> None:
        self._ftp_client = ftp_client

    def download(self, remote_path: str, local_path: str) -> TransferTask:
        total_size = self._resolve_remote_size(remote_path)
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=total_size,
            status=TransferStatus.RUNNING,
        )

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        payload = b"x" * total_size if total_size else b""
        Path(local_path).write_bytes(payload)
        task.transferred_size = len(payload)
        task.status = TransferStatus.COMPLETED
        return task

    def resume_download(self, remote_path: str, local_path: str) -> TransferTask:
        total_size = self._resolve_remote_size(remote_path)
        transferred_size = compute_resume_position(local_path)
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=total_size,
            transferred_size=transferred_size,
            status=TransferStatus.RUNNING,
        )

        if transferred_size >= total_size:
            task.status = TransferStatus.COMPLETED
            return task

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        remaining = total_size - transferred_size
        with open(local_path, "ab") as local_file:
            local_file.write(b"x" * remaining)

        task.transferred_size = total_size
        task.status = TransferStatus.COMPLETED
        return task

    def _resolve_remote_size(self, remote_path: str) -> int:
        if self._ftp_client is None:
            return 1024

        for remote_file in self._ftp_client.list_dir():
            if remote_file.path == remote_path:
                return remote_file.size

        return 1024


class MockUploader:
    """Mock uploader for GUI integration before a real FTP server is available."""

    def __init__(self, ftp_client: MockFTPClient | None = None) -> None:
        self._ftp_client = ftp_client
        self.files: dict[str, bytes] = {}

    def upload(self, local_path: str, remote_path: str) -> TransferTask:
        local_file = Path(local_path)
        payload = local_file.read_bytes()
        task = TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=len(payload),
            status=TransferStatus.RUNNING,
        )
        self.files[remote_path] = payload
        task.transferred_size = len(payload)
        task.status = TransferStatus.COMPLETED
        return task

    def resume_upload(self, local_path: str, remote_path: str) -> TransferTask:
        local_file = Path(local_path)
        payload = local_file.read_bytes()
        uploaded_size = len(self.files.get(remote_path, b""))
        task = TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=len(payload),
            transferred_size=uploaded_size,
            status=TransferStatus.RUNNING,
        )
        if uploaded_size > len(payload):
            raise ValueError("remote uploaded size exceeds local file size")
        self.files[remote_path] = payload
        task.transferred_size = len(payload)
        task.status = TransferStatus.COMPLETED
        return task


class ConsoleLogger:
    """Simple logger usable before the shared logger implementation lands."""

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

