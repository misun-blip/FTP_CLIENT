from ftp_client.app import create_app


def test_mock_services_can_complete_short_flow() -> None:
    app = create_app(use_mocks=True, with_gui=False)
    services = app.services

    assert services.ftp_client is not None
    assert services.logger is not None
    assert services.downloader is not None
    assert services.uploader is not None

    services.ftp_client.connect("127.0.0.1", 21)
    assert services.ftp_client.login("demo", "demo") is True

    files = services.ftp_client.list_dir()
    assert len(files) == 2
    assert files[0].is_dir is True


def test_mock_upload_and_download_services_can_transfer(tmp_path) -> None:
    app = create_app(use_mocks=True, with_gui=False)
    services = app.services
    assert services.downloader is not None
    assert services.uploader is not None
    assert services.ftp_client is not None
    services.ftp_client.connect("127.0.0.1", 21)
    services.ftp_client.login("demo", "demo")

    local_upload = tmp_path / "upload.txt"
    local_upload.write_bytes(b"payload")
    upload_task = services.uploader.upload(str(local_upload), "/upload.txt")
    assert upload_task.transferred_size == 7

    local_download = tmp_path / "download.txt"
    download_task = services.downloader.download("/demo.txt", str(local_download))
    assert download_task.transferred_size == 1024
    assert local_download.exists()


def test_real_app_wires_real_services_without_gui() -> None:
    app = create_app(with_gui=False)
    services = app.services

    assert services.ftp_client is not None
    assert services.downloader is services.ftp_client
    assert services.uploader is services.ftp_client
