"""FTP download module owned by member 3."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from ftp_client.core.connection import FTPConnection
from ftp_client.core.response_parser import FTPResponse, FTPResponseCode, ResponseParser
from ftp_client.interfaces import LoggerProtocol
from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import TransferDirection, TransferStatus, TransferTask
from ftp_client.transfer.download_resume import (
    CHUNK_SIZE,
    TransferError,
    compute_resume_position,
    perform_resume_download,
)


class Downloader:
    """Download files from the FTP server and report progress via TransferTask."""

    def __init__(
        self,
        connection: FTPConnection,
        *,
        logger: LoggerProtocol | None = None,
        list_dir: Callable[[str | None], list[RemoteFile]] | None = None,
        cwd: Callable[[str], bool] | None = None,
    ) -> None:
        self._connection = connection
        self._logger = logger
        self._list_dir = list_dir
        self._cwd = cwd

    def download(self, remote_path: str, local_path: str) -> TransferTask:
        """Download a remote file to the local path."""
        self._log_info(f"下载文件: {remote_path} -> {local_path}")

        file_size = self._get_remote_file_size(remote_path)
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=file_size,
            status=TransferStatus.RUNNING,
        )

        try:
            self._perform_download(remote_path, local_path, task)
            task.status = TransferStatus.COMPLETED
            self._log_info(f"下载完成: {remote_path}")
        except Exception as exc:
            task.status = TransferStatus.FAILED
            self._log_error(f"下载失败: {exc}")
            raise

        return task

    def resume_download(self, remote_path: str, local_path: str) -> TransferTask:
        """Resume a partially downloaded file from the local checkpoint."""
        self._log_info(f"断点续传下载: {remote_path} -> {local_path}")

        transferred_size = compute_resume_position(local_path)
        file_size = self._get_remote_file_size(remote_path)
        task = TransferTask(
            direction=TransferDirection.DOWNLOAD,
            local_path=local_path,
            remote_path=remote_path,
            total_size=file_size,
            transferred_size=transferred_size,
            status=TransferStatus.RUNNING,
        )

        if transferred_size >= file_size:
            task.status = TransferStatus.COMPLETED
            return task

        try:
            perform_resume_download(
                self._connection,
                remote_path,
                local_path,
                transferred_size,
                task,
                set_binary_mode=self._set_binary_mode,
                enter_pasv=self._enter_pasv_mode,
                receive_final=self._receive_final_response,
            )
            task.status = TransferStatus.COMPLETED
            self._log_info(f"断点续传完成: {remote_path}")
        except Exception as exc:
            task.status = TransferStatus.FAILED
            self._log_error(f"断点续传失败: {exc}")
            raise

        return task

    def _perform_download(
        self,
        remote_path: str,
        local_path: str,
        task: TransferTask,
    ) -> None:
        self._set_binary_mode()
        pasv_response = self._enter_pasv_mode()

        self._connection.send_command(f"RETR {remote_path}")
        self._connection.setup_data_connection(pasv_response.raw)

        Path(local_path).parent.mkdir(parents=True, exist_ok=True)

        received_size = 0
        with open(local_path, "wb") as local_file:
            while True:
                chunk = self._connection.data_socket.recv(CHUNK_SIZE)
                if not chunk:
                    break
                local_file.write(chunk)
                received_size += len(chunk)
                task.transferred_size = received_size

        self._connection.close_data_connection()

        final_response = self._receive_final_response()
        if final_response.code != FTPResponseCode.CLOSING_DATA_CONNECTION:
            raise TransferError(f"传输异常: {final_response.message}")

    def _set_binary_mode(self) -> None:
        response_raw = self._connection.send_command("TYPE I")
        response = FTPResponse.parse(response_raw)
        if not ResponseParser.validate_type_response(response):
            raise TransferError(f"设置传输类型失败: {response.message}")

    def _enter_pasv_mode(self) -> FTPResponse:
        response_raw = self._connection.send_command("PASV")
        response = FTPResponse.parse(response_raw)
        if not ResponseParser.validate_pasv_response(response):
            raise TransferError(f"进入被动模式失败: {response.message}")
        return response

    def _receive_final_response(self) -> FTPResponse:
        return self._connection._receive_response()

    def _get_remote_file_size(self, remote_path: str) -> int:
        response_raw = self._connection.send_command(f"SIZE {remote_path}")
        response = FTPResponse.parse(response_raw)

        if response.code == 213:
            try:
                return int(response.message.strip())
            except ValueError:
                return 0

        return self._get_remote_file_size_from_list(remote_path)

    def _get_remote_file_size_from_list(self, remote_path: str) -> int:
        if self._list_dir is None:
            return 0

        parent_dir = str(Path(remote_path).parent)
        if parent_dir not in (".", "") and self._cwd is not None:
            try:
                self._cwd(parent_dir)
            except Exception:
                pass

        file_name = Path(remote_path).name
        for remote_file in self._list_dir(None):
            if remote_file.name == file_name:
                return remote_file.size

        return 0

    def _log_info(self, message: str) -> None:
        if self._logger is not None:
            self._logger.info(message)

    def _log_error(self, message: str) -> None:
        if self._logger is not None:
            self._logger.error(message)
