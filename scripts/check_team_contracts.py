from __future__ import annotations

import inspect
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ftp_client.interfaces import (
    DownloaderProtocol,
    FTPClientProtocol,
    LoggerProtocol,
    MainWindowProtocol,
    UploaderProtocol,
)


CONTRACTS = {
    "FTPClientProtocol": (FTPClientProtocol, ("connect", "login", "list_dir", "close")),
    "DownloaderProtocol": (DownloaderProtocol, ("download", "resume_download")),
    "UploaderProtocol": (UploaderProtocol, ("upload", "resume_upload")),
    "LoggerProtocol": (LoggerProtocol, ("info", "error")),
    "MainWindowProtocol": (MainWindowProtocol, ("show",)),
}


def main() -> None:
    for name, (contract, required_methods) in CONTRACTS.items():
        available = {
            method_name
            for method_name, value in inspect.getmembers(contract, inspect.isfunction)
            if not method_name.startswith("_")
        }
        missing = set(required_methods) - available
        if missing:
            raise SystemExit(f"{name} missing methods: {sorted(missing)}")
        print(f"{name}: ok")


if __name__ == "__main__":
    main()

