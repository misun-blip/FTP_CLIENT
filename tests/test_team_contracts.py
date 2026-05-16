from ftp_client.interfaces import (
    DownloaderProtocol,
    LoggerProtocol,
    MainWindowProtocol,
    UploaderProtocol,
)


def test_team_contracts_are_available() -> None:
    assert DownloaderProtocol.__name__ == "DownloaderProtocol"
    assert UploaderProtocol.__name__ == "UploaderProtocol"
    assert LoggerProtocol.__name__ == "LoggerProtocol"
    assert MainWindowProtocol.__name__ == "MainWindowProtocol"

