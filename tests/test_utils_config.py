from __future__ import annotations

import pytest

from ftp_client.utils.config import AppConfig, ConfigManager, load_config, save_config
from ftp_client.utils.exceptions import ConfigError


def test_load_config_returns_defaults_when_missing(tmp_path) -> None:
    config = load_config(tmp_path / "missing.json")

    assert config.host == "127.0.0.1"
    assert config.port == 21
    assert config.timeout == 10


def test_save_and_load_config_round_trip(tmp_path) -> None:
    config_path = tmp_path / "settings" / "ftp.json"
    config = AppConfig(
        host="ftp.example.test",
        port=2121,
        timeout=30,
        username="demo",
        default_download_dir="D:/downloads",
        log_level="debug",
        recent_connections=[{"host": "ftp.example.test", "port": 2121}],
    )

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded.host == "ftp.example.test"
    assert loaded.port == 2121
    assert loaded.timeout == 30
    assert loaded.log_level == "DEBUG"
    assert loaded.recent_connections == [{"host": "ftp.example.test", "port": 2121}]


def test_invalid_config_json_raises_config_error(tmp_path) -> None:
    config_path = tmp_path / "broken.json"
    config_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(config_path)


def test_invalid_config_values_are_rejected() -> None:
    with pytest.raises(ConfigError, match="port"):
        AppConfig(port=70000).to_dict()

    with pytest.raises(ConfigError, match="timeout"):
        AppConfig(timeout=0).to_dict()

    with pytest.raises(ConfigError, match="log level"):
        AppConfig(log_level="LOUD").to_dict()


def test_config_manager_can_reload_saved_changes(tmp_path) -> None:
    config_path = tmp_path / "ftp.json"
    manager = ConfigManager(config_path)
    manager.config.host = "first.example.test"
    manager.save()

    save_config(AppConfig(host="second.example.test"), config_path)

    assert manager.reload().host == "second.example.test"
