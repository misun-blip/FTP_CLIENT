from __future__ import annotations

from dataclasses import dataclass

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
        """Run the application.

        GUI 完成前先提供一个最小可运行入口，避免仓库长期处于“还不能启动”的状态。
        """
        if self.services.main_window is not None:
            show = getattr(self.services.main_window, "show", None)
            if callable(show):
                show()
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
    if use_mocks:
        services.ftp_client = MockFTPClient()
        services.logger = ConsoleLogger()
    return FTPApplication(services)
