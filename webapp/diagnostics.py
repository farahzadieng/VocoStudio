"""Startup checks shown on the local dashboard."""

from __future__ import annotations

import os
import platform
import uuid
from dataclasses import dataclass

from .config import AppConfig
from .device import DeviceChoice, choose_device
from .model_catalog import MODEL_CATALOG
from .model_manager import validate_checkpoint


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    device: DeviceChoice
    models_ready: int
    unavailable_models: tuple[str, ...]
    ffmpeg_available: bool
    operating_system: str
    fatal_errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "device": self.device.label_fa,
            "device_name": self.device.name,
            "models_ready": self.models_ready,
            "unavailable_models": list(self.unavailable_models),
            "ffmpeg_available": self.ffmpeg_available,
            "operating_system": self.operating_system,
            "fatal_errors": list(self.fatal_errors),
            "warnings": list(self.warnings),
        }


def run_diagnostics(config: AppConfig, torch_module, ffmpeg_path: str | None) -> DiagnosticReport:
    fatal: list[str] = []
    warnings: list[str] = []
    source = config.repository_root / "clearvoice"
    if not source.is_dir():
        fatal.append("پوشه clearvoice در ریشه پروژه پیدا نشد.")
    try:
        config.runtime_root.mkdir(parents=True, exist_ok=True)
        probe = config.runtime_root / f".write-test-{uuid.uuid4().hex}"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        fatal.append(f"پوشه فایل‌های موقت قابل نوشتن نیست: {exc}")
    try:
        device = choose_device(torch_module, os.getenv("CLEARVOICE_DEVICE", "auto"))
    except ValueError as exc:
        fatal.append(str(exc))
        device = DeviceChoice("cpu", "پردازنده اصلی (CPU)")
    unavailable: list[str] = []
    for name, spec in MODEL_CATALOG.items():
        try:
            validate_checkpoint(config.checkpoints_root, spec)
        except Exception as exc:
            unavailable.append(name)
            warnings.append(str(exc))
    if not ffmpeg_path:
        warnings.append("FFmpeg پیدا نشد؛ فقط فرمت‌های مستقیم WAV و FLAC فعال هستند.")
    return DiagnosticReport(
        device=device,
        models_ready=len(MODEL_CATALOG) - len(unavailable),
        unavailable_models=tuple(unavailable),
        ffmpeg_available=bool(ffmpeg_path),
        operating_system=f"{platform.system()} {platform.machine()}",
        fatal_errors=tuple(fatal),
        warnings=tuple(warnings),
    )
