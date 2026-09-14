"""Filesystem and runtime configuration."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    repository_root: Path
    checkpoints_root: Path
    runtime_root: Path
    max_upload_bytes: int = 500 * 1024 * 1024
    retention_hours: int = 24

    @classmethod
    def discover(cls, repository_root: Path | None = None) -> "AppConfig":
        root = (repository_root or Path(__file__).resolve().parents[1]).resolve()
        return cls(root, root / "checkpoints", root / "webapp" / "runtime")

