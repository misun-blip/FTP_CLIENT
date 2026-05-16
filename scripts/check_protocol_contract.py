from __future__ import annotations

import inspect
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ftp_client.interfaces import FTPClientProtocol


REQUIRED_METHODS = ("connect", "login", "list_dir", "close")


def main() -> None:
    protocol_methods = {
        name for name, value in inspect.getmembers(FTPClientProtocol, inspect.isfunction)
        if not name.startswith("_")
    }
    missing = set(REQUIRED_METHODS) - protocol_methods

    if missing:
        raise SystemExit(f"FTPClientProtocol is missing required methods: {sorted(missing)}")

    print("FTP protocol contract is ready.")
    print("Required methods:")
    for method in REQUIRED_METHODS:
        print(f"- {method}")


if __name__ == "__main__":
    main()

