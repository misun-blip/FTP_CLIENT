from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


class TransferDirection(str, Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


class TransferStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TransferTask:
    """Shared transfer model used by uploader, downloader, task manager and UI."""

    direction: TransferDirection
    local_path: str
    remote_path: str
    total_size: int
    transferred_size: int = 0
    status: TransferStatus = TransferStatus.PENDING
    task_id: str = ""
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id:
            self.task_id = uuid4().hex
        if self.total_size < 0:
            raise ValueError("total_size must be non-negative")
        if self.transferred_size < 0:
            raise ValueError("transferred_size must be non-negative")
        if self.transferred_size > self.total_size:
            raise ValueError("transferred_size cannot exceed total_size")

    @property
    def progress(self) -> float:
        if self.total_size == 0:
            return 0.0
        return self.transferred_size / self.total_size

