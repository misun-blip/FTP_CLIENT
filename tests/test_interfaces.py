from ftp_client.interfaces import (
    DownloaderProtocol,
    FTPClientProtocol,
    LoggerProtocol,
    MainWindowProtocol,
    UploaderProtocol,
)


def test_protocol_names_are_available() -> None:
    assert FTPClientProtocol.__name__ == "FTPClientProtocol"
    assert DownloaderProtocol.__name__ == "DownloaderProtocol"
    assert UploaderProtocol.__name__ == "UploaderProtocol"
    assert LoggerProtocol.__name__ == "LoggerProtocol"
    assert MainWindowProtocol.__name__ == "MainWindowProtocol"

