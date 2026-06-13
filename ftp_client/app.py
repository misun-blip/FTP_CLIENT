from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication

from ftp_client.interfaces import (
    DownloaderProtocol,
    FTPClientProtocol,
    LoggerProtocol,
    MainWindowProtocol,
    UploaderProtocol,
)
from ftp_client.mocks import ConsoleLogger, MockFTPClient
from ftp_client.models.remote_file import RemoteFile
from ftp_client.models.transfer_task import TransferTask

_qt_app: QApplication | None = None


@dataclass(slots=True)
class ApplicationServices:
    """Application-level dependency container.

    该对象只负责汇总各模块，后续由各负责人将具体实现注入进来。
    """

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
            _qt_app = QApplication.instance()
            if _qt_app is not None:
                _qt_app.exec()
            return

        print("FTP client skeleton is ready.")
        print("Integrated models:")
        print(f"- RemoteFile: {RemoteFile.__name__}")
        print(f"- TransferTask: {TransferTask.__name__}")


def create_app(*, use_mocks: bool = False) -> FTPApplication:
    """Create the application shell.

    后续联调时，各模块负责人只需在这里接入自己的实现。
    """
    services = ApplicationServices()

    # 初始化 Qt 应用（必须在创建任何 widget 之前）
    qt_app = QApplication.instance()
    if qt_app is None:
        qt_app = QApplication([])

    if use_mocks:
        services.ftp_client = MockFTPClient()
        services.logger = ConsoleLogger()

    # 注入 GUI
    from ftp_client.ui.main_window import MainWindow

    services.main_window = MainWindow(
        ftp=services.ftp_client,
        downloader=services.downloader,
        uploader=services.uploader,
        logger=services.logger,
    )
    return FTPApplication(services)
