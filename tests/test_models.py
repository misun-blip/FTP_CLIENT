from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import (
    TransferDirection,
    TransferStatus,
    TransferTask,
)


def test_remote_file_is_constructible() -> None:
    item = RemoteFile(
        name="demo.txt",
        path="/demo.txt",
        size=128,
        is_dir=False,
        modified_time="2026-05-16 12:00:00",
    )

    assert item.name == "demo.txt"
    assert item.size == 128
    assert item.is_dir is False


def test_transfer_task_generates_id_and_progress() -> None:
    task = TransferTask(
        direction=TransferDirection.DOWNLOAD,
        local_path="demo.txt",
        remote_path="/demo.txt",
        total_size=100,
        transferred_size=25,
    )

    assert task.task_id
    assert task.status is TransferStatus.PENDING
    assert task.progress == 0.25

