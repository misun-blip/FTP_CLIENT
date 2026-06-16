from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ftp_client.utils.exceptions import ConfigError


DEFAULT_CONFIG_PATH = Path("ftp_client_config.json")


@dataclass(slots=True)
class AppConfig:
    """Runtime configuration maintained by the utility owner."""

    host: str = "127.0.0.1"
    port: int = 21
    timeout: int = 10
    username: str = ""
    default_download_dir: str = "downloads"
    log_level: str = "INFO"
    recent_connections: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        config = cls(
            host=str(data.get("host", cls.host)),
            port=_read_int(data.get("port", cls.port), "port"),
            timeout=_read_int(data.get("timeout", cls.timeout), "timeout"),
            username=str(data.get("username", cls.username)),
            default_download_dir=str(
                data.get("default_download_dir", cls.default_download_dir)
            ),
            log_level=str(data.get("log_level", cls.log_level)).upper(),
            recent_connections=list(data.get("recent_connections", [])),
        )
        config.validate()
        return config

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "username": self.username,
            "default_download_dir": self.default_download_dir,
            "log_level": self.log_level,
            "recent_connections": self.recent_connections,
        }

    def validate(self) -> None:
        if not self.host.strip():
            raise ConfigError("host cannot be empty")
        if not 1 <= self.port <= 65535:
            raise ConfigError("port must be between 1 and 65535")
        if self.timeout <= 0:
            raise ConfigError("timeout must be greater than 0")
        if self.log_level.upper() not in logging._nameToLevel:
            raise ConfigError(f"unsupported log level: {self.log_level}")
        if not isinstance(self.recent_connections, list):
            raise ConfigError("recent_connections must be a list")


def _read_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ConfigError(f"{field_name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{field_name} must be an integer") from exc


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load configuration from JSON; return defaults when the file is absent."""
    config_path = Path(path)
    if not config_path.exists():
        return AppConfig()

    try:
        raw_data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid config json: {config_path}") from exc

    if not isinstance(raw_data, dict):
        raise ConfigError("config root must be a JSON object")

    return AppConfig.from_dict(raw_data)


def save_config(config: AppConfig, path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    """Persist configuration as pretty JSON."""
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class ConfigManager:
    """Convenience wrapper for modules that keep one config file open."""

    def __init__(self, path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.path = Path(path)
        self.config = load_config(self.path)

    def save(self) -> None:
        save_config(self.config, self.path)

    def reload(self) -> AppConfig:
        self.config = load_config(self.path)
        return self.config
