from __future__ import annotations

from ftp_client.models.transfer_task import TransferTask


class DownloaderTemplate:
    """Implementation template for the download owner."""

    def download(self, remote_path: str, local_path: str) -> TransferTask:
        raise NotImplementedError

    def resume_download(self, remote_path: str, local_path: str) -> TransferTask:
        raise NotImplementedError

