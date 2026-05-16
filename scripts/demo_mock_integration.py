from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ftp_client.app import create_app


def main() -> None:
    app = create_app(use_mocks=True)
    services = app.services

    assert services.ftp_client is not None
    assert services.logger is not None

    services.logger.info("start mock integration demo")
    services.ftp_client.connect("127.0.0.1", 21)
    services.logger.info("connected")
    services.ftp_client.login("demo", "demo")
    services.logger.info("logged in")

    files = services.ftp_client.list_dir()
    services.logger.info(f"received {len(files)} remote entries")
    for item in files:
        kind = "DIR" if item.is_dir else "FILE"
        print(f"{kind:4} {item.path} ({item.size} bytes)")


if __name__ == "__main__":
    main()
