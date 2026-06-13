"""Download resume helpers owned by the download module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from ftp_client.core.response_parser import FTPResponse, FTPResponseCode

if TYPE_CHECKING:
    from ftp_client.core.connection import FTPConnection
    from ftp_client.models.transfer_task import TransferTask


class TransferError(Exception):
    """Raised when a download transfer fails."""


CHUNK_SIZE = 8192


def compute_resume_position(local_path: str) -> int:
    """Return how many bytes are already present in the local partial file."""
    local_file = Path(local_path)
    return local_file.stat().st_size if local_file.exists() else 0


def perform_resume_download(
    connection: FTPConnection,
    remote_path: str,
    local_path: str,
    resume_pos: int,
    task: TransferTask,
    *,
    set_binary_mode: Callable[[], None],
    enter_pasv: Callable[[], FTPResponse],
    receive_final: Callable[[], FTPResponse],
) -> None:
    """Continue a download from ``resume_pos`` using REST + RETR."""
    set_binary_mode()

    if resume_pos > 0:
        rest_response_raw = connection.send_command(f"REST {resume_pos}")
        rest_response = FTPResponse.parse(rest_response_raw)
        if rest_response.code != FTPResponseCode.FILE_ACTION_PENDING:
            raise TransferError(f"不支持断点续传: {rest_response.message}")

    pasv_response = enter_pasv()
    connection.send_command(f"RETR {remote_path}")
    connection.setup_data_connection(pasv_response.raw)

    received_size = resume_pos
    with open(local_path, "ab") as local_file:
        while received_size < task.total_size:
            chunk = connection.data_socket.recv(CHUNK_SIZE)
            if not chunk:
                break
            local_file.write(chunk)
            received_size += len(chunk)
            task.transferred_size = received_size

    connection.close_data_connection()

    final_response = receive_final()
    if final_response.code != FTPResponseCode.CLOSING_DATA_CONNECTION:
        raise TransferError(f"传输异常: {final_response.message}")
