from __future__ import annotations

from ftp_client.models.transfer_task import TransferTask


class UploaderTemplate:
    """Implementation template for the upload owner."""

    def upload(self, local_path: str, remote_path: str) -> TransferTask:
        raise NotImplementedError

    def resume_upload(self, local_path: str, remote_path: str) -> TransferTask:
        raise NotImplementedError

