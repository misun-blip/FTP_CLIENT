from __future__ import annotations

from dataclasses import dataclass

from ftp_client.interfaces import (
    DownloaderProtocol,
    FTPClientProtocol,
    LoggerProtocol,
    MainWindowProtocol,
    UploaderProtocol,
)
from ftp_client.mocks import ConsoleLogger, MockDownloader, MockFTPClient, MockUploader
from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import TransferTask

_qt_app: object | None = None


@dataclass(slots=True)
class ApplicationServices:
    """Application-level dependency container."""

    ftp_client: FTPClientProtocol | None = None
    downloader: DownloaderProtocol | None = None
    uploader: UploaderProtocol | None = None
    task_manager: object | None = None
    logger: LoggerProtocol | None = None
    config: object | None = None
    main_window: MainWindowProtocol | None = None


class FTPApplication:
    """Main application shell owned by the integration layer."""

    def __init__(self, services: ApplicationServices | None = None) -> None:
        self.services = services or ApplicationServices()

    def run(self) -> None:
        """Run the application."""
        if self.services.main_window is not None:
            window = self.services.main_window
            window.show()
            global _qt_app
            try:
                from PySide6.QtWidgets import QApplication
            except ModuleNotFoundError as exc:
                raise RuntimeError("PySide6 is required to launch the GUI") from exc
            _qt_app = QApplication.instance()
            if _qt_app is not None:
                _qt_app.exec()
            return

        print("FTP client services are ready, but PySide6 is not installed.")
        print("Install dependencies with: pip install -r requirements.txt")
        print("Integrated models:")
        print(f"- RemoteFile: {RemoteFile.__name__}")
        print(f"- TransferTask: {TransferTask.__name__}")


def create_app(*, use_mocks: bool = False, with_gui: bool = True) -> FTPApplication:
    """Create the application shell with mock or real FTP services."""
    services = ApplicationServices()

    if use_mocks:
        services.ftp_client = MockFTPClient()
        services.logger = ConsoleLogger()
        services.downloader = MockDownloader(services.ftp_client)
        services.uploader = MockUploader(services.ftp_client)
    else:
        from ftp_client.core.ftp_client import FTPClient

        ftp_client = FTPClient()
        services.ftp_client = ftp_client
        services.downloader = ftp_client
        services.uploader = ftp_client
        services.logger = ConsoleLogger()

    if not with_gui:
        return FTPApplication(services)

    try:
        from PySide6.QtWidgets import QApplication
        from ftp_client.ui.main_window import MainWindow
    except ModuleNotFoundError:
        return FTPApplication(services)

    qt_app = QApplication.instance()
    if qt_app is None:
        qt_app = QApplication([])

    services.main_window = MainWindow(
        ftp=services.ftp_client,
        downloader=services.downloader,
        uploader=services.uploader,
        logger=services.logger,
    )
    return FTPApplication(services)
