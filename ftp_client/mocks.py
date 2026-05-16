from __future__ import annotations

from ftp_client.models.remote_file import RemoteFile


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


class ConsoleLogger:
    """Simple logger usable before the shared logger implementation lands."""

    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")

