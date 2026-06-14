from pathlib import Path

import pytest

from ftp_client.models.transfer_task import TransferDirection, TransferStatus
from ftp_client.transfer.uploader_template import MemoryUploadStorage, UploaderTemplate


def test_upload_writes_file_and_returns_completed_task(tmp_path: Path) -> None:
    local_file = tmp_path / "demo.txt"
    local_file.write_bytes(b"hello ftp")
    storage = MemoryUploadStorage()
    uploader = UploaderTemplate(storage)

    task = uploader.upload(str(local_file), "/remote/demo.txt")

    assert task.direction is TransferDirection.UPLOAD
    assert task.local_path == str(local_file)
    assert task.remote_path == "/remote/demo.txt"
    assert task.total_size == 9
    assert task.transferred_size == 9
    assert task.status is TransferStatus.COMPLETED
    assert task.progress == 1.0
    assert storage.files["/remote/demo.txt"] == b"hello ftp"


def test_resume_upload_continues_from_uploaded_size(tmp_path: Path) -> None:
    local_file = tmp_path / "large.bin"
    local_file.write_bytes(b"abcdef")
    storage = MemoryUploadStorage()
    storage.write_upload("/remote/large.bin", b"abc")
    uploader = UploaderTemplate(storage)

    task = uploader.resume_upload(str(local_file), "/remote/large.bin")

    assert task.total_size == 6
    assert task.transferred_size == 6
    assert task.status is TransferStatus.COMPLETED
    assert storage.files["/remote/large.bin"] == b"abcdef"


def test_upload_requires_existing_local_file(tmp_path: Path) -> None:
    uploader = UploaderTemplate()

    with pytest.raises(FileNotFoundError):
        uploader.upload(str(tmp_path / "missing.txt"), "/remote/missing.txt")


def test_resume_upload_rejects_remote_size_larger_than_local(tmp_path: Path) -> None:
    local_file = tmp_path / "small.txt"
    local_file.write_bytes(b"abc")
    storage = MemoryUploadStorage()
    storage.write_upload("/remote/small.txt", b"abcdef")
    uploader = UploaderTemplate(storage)

    with pytest.raises(ValueError, match="remote uploaded size"):
        uploader.resume_upload(str(local_file), "/remote/small.txt")
