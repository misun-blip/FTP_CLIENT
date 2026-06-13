from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ftp_client.mocks import MockDownloader, MockFTPClient
from ftp_client.models.transfer_task import TransferDirection, TransferStatus
from ftp_client.transfer.download_resume import compute_resume_position, perform_resume_download
from ftp_client.transfer.downloader import Downloader
from ftp_client.models.transfer_task import TransferTask


def _make_ftp_response(code: int, message: str, raw: str | None = None) -> MagicMock:
    response = MagicMock()
    response.code = code
    response.message = message
    response.raw = raw or f"{code} {message}"
    return response


def test_compute_resume_position_for_missing_file(tmp_path: Path) -> None:
    assert compute_resume_position(str(tmp_path / "missing.bin")) == 0


def test_compute_resume_position_for_partial_file(tmp_path: Path) -> None:
    partial = tmp_path / "partial.bin"
    partial.write_bytes(b"abc")
    assert compute_resume_position(str(partial)) == 3


def test_downloader_download_writes_file_and_returns_task(tmp_path: Path) -> None:
    local_path = tmp_path / "demo.txt"
    connection = MagicMock()
    connection.send_command.side_effect = [
        "213 4",
        "200 Type set to I.",
        "227 Entering Passive Mode (127,0,0,1,7,208)",
        "150 Opening data connection.",
    ]
    connection.data_socket.recv.side_effect = [b"data", b""]
    connection._receive_response.return_value = _make_ftp_response(
        226, "Transfer complete", "226 Transfer complete"
    )

    downloader = Downloader(connection)
    with patch("ftp_client.transfer.downloader.FTPResponse.parse") as parse_mock:
        parse_mock.side_effect = [
            _make_ftp_response(213, "4"),
            _make_ftp_response(200, "Type set to I."),
            _make_ftp_response(227, "Entering Passive Mode (127,0,0,1,7,208)"),
            _make_ftp_response(226, "Transfer complete"),
        ]

        task = downloader.download("/demo.txt", str(local_path))

    assert task.direction == TransferDirection.DOWNLOAD
    assert task.status == TransferStatus.COMPLETED
    assert task.total_size == 4
    assert task.transferred_size == 4
    assert local_path.read_bytes() == b"data"


def test_downloader_resume_download_appends_from_checkpoint(tmp_path: Path) -> None:
    local_path = tmp_path / "demo.txt"
    local_path.write_bytes(b"ab")

    connection = MagicMock()
    connection.send_command.side_effect = [
        "213 4",
        "200 Type set to I.",
        "350 Restarting at 2.",
        "227 Entering Passive Mode (127,0,0,1,7,208)",
        "150 Opening data connection.",
    ]
    connection.data_socket.recv.side_effect = [b"cd", b""]
    connection._receive_response.return_value = _make_ftp_response(
        226, "Transfer complete", "226 Transfer complete"
    )

    downloader = Downloader(connection)
    with patch("ftp_client.transfer.downloader.FTPResponse.parse") as parse_mock:
        parse_mock.side_effect = [
            _make_ftp_response(213, "4"),
            _make_ftp_response(200, "Type set to I."),
            _make_ftp_response(350, "Restarting at 2."),
            _make_ftp_response(227, "Entering Passive Mode (127,0,0,1,7,208)"),
            _make_ftp_response(226, "Transfer complete"),
        ]

        task = downloader.resume_download("/demo.txt", str(local_path))

    assert task.status == TransferStatus.COMPLETED
    assert task.transferred_size == 4
    assert local_path.read_bytes() == b"abcd"


def test_resume_download_skips_when_already_complete(tmp_path: Path) -> None:
    local_path = tmp_path / "demo.txt"
    local_path.write_bytes(b"done")

    connection = MagicMock()
    connection.send_command.return_value = "213 4"

    downloader = Downloader(connection)
    with patch("ftp_client.transfer.downloader.FTPResponse.parse") as parse_mock:
        parse_mock.return_value = _make_ftp_response(213, "4")
        task = downloader.resume_download("/demo.txt", str(local_path))

    assert task.status == TransferStatus.COMPLETED
    assert task.transferred_size == 4
    connection.send_command.assert_called_once_with("SIZE /demo.txt")


def test_perform_resume_download_rejects_unsupported_rest(tmp_path: Path) -> None:
    local_path = tmp_path / "demo.txt"
    local_path.write_bytes(b"x")

    connection = MagicMock()
    connection.send_command.return_value = "502 Command not implemented."

    task = TransferTask(
        direction=TransferDirection.DOWNLOAD,
        local_path=str(local_path),
        remote_path="/demo.txt",
        total_size=10,
        transferred_size=1,
    )

    with patch("ftp_client.transfer.download_resume.FTPResponse.parse") as parse_mock:
        parse_mock.return_value = _make_ftp_response(502, "Command not implemented.")
        with pytest.raises(Exception, match="不支持断点续传"):
            perform_resume_download(
                connection,
                "/demo.txt",
                str(local_path),
                1,
                task,
                set_binary_mode=MagicMock(),
                enter_pasv=MagicMock(),
                receive_final=MagicMock(),
            )


def test_mock_downloader_download_and_resume(tmp_path: Path) -> None:
    ftp_client = MockFTPClient()
    ftp_client.connect("127.0.0.1", 21)
    ftp_client.login("user", "pass")

    downloader = MockDownloader(ftp_client)
    local_path = tmp_path / "demo.txt"

    task = downloader.download("/demo.txt", str(local_path))
    assert task.status == TransferStatus.COMPLETED
    assert local_path.stat().st_size == 1024

    partial_path = tmp_path / "partial.txt"
    partial_path.write_bytes(b"x" * 512)
    resume_task = downloader.resume_download("/demo.txt", str(partial_path))
    assert resume_task.status == TransferStatus.COMPLETED
    assert partial_path.stat().st_size == 1024
