from __future__ import annotations

from ftp_client.models.remote_file import RemoteFile


class FTPClientTemplate:
    """Implementation template for the protocol owner.

    该文件仅作为接入模板，正式实现可在 `ftp_client.py` 中完成。
    """

    def connect(self, host: str, port: int, timeout: int = 10) -> None:
        raise NotImplementedError

    def login(self, username: str, password: str) -> bool:
        raise NotImplementedError

    def list_dir(self, path: str | None = None) -> list[RemoteFile]:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

