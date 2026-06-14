from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ftp_client.models.transfer_task import (
    TransferDirection,
    TransferStatus,
    TransferTask,
)


class UploadStorage(Protocol):
    """Storage backend used by the uploader to persist outgoing bytes."""

    def get_uploaded_size(self, remote_path: str) -> int: ...

    def write_upload(self, remote_path: str, data: bytes, offset: int = 0) -> int: ...


class MemoryUploadStorage:
    """In-memory upload backend for local integration tests and early wiring."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def get_uploaded_size(self, remote_path: str) -> int:
        return len(self.files.get(remote_path, b""))

    def write_upload(self, remote_path: str, data: bytes, offset: int = 0) -> int:
        existing = self.files.get(remote_path, b"")
        if offset > len(existing):
            raise ValueError("resume offset cannot exceed uploaded size")

        merged = existing[:offset] + data
        self.files[remote_path] = merged
        return len(data)


class UploaderTemplate:
    """File upload implementation matching the shared uploader contract."""

    def __init__(self, storage: UploadStorage | None = None) -> None:
        self.storage = storage or MemoryUploadStorage()

    def upload(self, local_path: str, remote_path: str) -> TransferTask:
        source = self._require_file(local_path)
        data = source.read_bytes()
        transferred = self.storage.write_upload(remote_path, data, offset=0)

        return TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=str(source),
            remote_path=remote_path,
            total_size=len(data),
            transferred_size=transferred,
            status=TransferStatus.COMPLETED,
        )

    def resume_upload(self, local_path: str, remote_path: str) -> TransferTask:
        source = self._require_file(local_path)
        total_size = source.stat().st_size
        uploaded_size = self.storage.get_uploaded_size(remote_path)

        if uploaded_size > total_size:
            raise ValueError("remote uploaded size exceeds local file size")

        with source.open("rb") as file_obj:
            file_obj.seek(uploaded_size)
            data = file_obj.read()

        transferred = self.storage.write_upload(
            remote_path,
            data,
            offset=uploaded_size,
        )

        return TransferTask(
            direction=TransferDirection.UPLOAD,
            local_path=str(source),
            remote_path=remote_path,
            total_size=total_size,
            transferred_size=uploaded_size + transferred,
            status=TransferStatus.COMPLETED,
        )

    def _require_file(self, local_path: str) -> Path:
        source = Path(local_path)
        if not source.exists():
            raise FileNotFoundError(local_path)
        if not source.is_file():
            raise ValueError("local_path must point to a file")
        return source

