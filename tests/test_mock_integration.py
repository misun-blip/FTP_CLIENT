from ftp_client.app import create_app


def test_mock_services_can_complete_short_flow() -> None:
    app = create_app(use_mocks=True)
    services = app.services

    assert services.ftp_client is not None
    assert services.logger is not None

    services.ftp_client.connect("127.0.0.1", 21)
    assert services.ftp_client.login("demo", "demo") is True

    files = services.ftp_client.list_dir()
    assert len(files) == 2
    assert files[0].is_dir is True

