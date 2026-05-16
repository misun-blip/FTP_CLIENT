from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RemoteFile:
    """Normalized remote file entry used across protocol and UI layers."""

    name: str
    path: str
    size: int
    is_dir: bool
    modified_time: str | None = None

