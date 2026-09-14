"""Strict offline checkpoint validation and lazy ClearVoice lifecycle."""

from __future__ import annotations

import gc
import shutil
import threading
from pathlib import Path
from typing import Callable

from .device import DeviceChoice, is_mps_fallback_error
from .errors import CheckpointError
from .model_catalog import ModelSpec, get_model_spec


def clear_partial_outputs(output_path: str | Path) -> None:
    """Remove files left by a failed attempt before a safe retry."""

    root = Path(output_path)
    if not root.is_dir():
        return
    for child in root.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)


def validate_checkpoint(checkpoints_root: Path, spec: ModelSpec) -> tuple[Path, ...]:
    model_dir = (Path(checkpoints_root) / spec.checkpoint_dir).resolve()
    if not model_dir.is_dir():
        raise CheckpointError(
            f"پوشه مدل {spec.name} پیدا نشد.", str(model_dir)
        )
    manifest = model_dir / "last_best_checkpoint"
    if not manifest.is_file():
        raise CheckpointError(
            f"فایل راهنمای checkpoint مدل {spec.name} پیدا نشد.", str(manifest)
        )
    try:
        entries = [line.strip() for line in manifest.read_text().splitlines() if line.strip()]
    except OSError as exc:
        raise CheckpointError(
            f"فایل checkpoint مدل {spec.name} خوانده نشد.", str(exc)
        ) from exc
    if not entries:
        raise CheckpointError(
            f"فایل راهنمای checkpoint مدل {spec.name} خالی است.", str(manifest)
        )
    resolved: list[Path] = []
    for entry in entries:
        relative = Path(entry)
        if relative.is_absolute() or ".." in relative.parts:
            raise CheckpointError(
                f"مسیر checkpoint مدل {spec.name} معتبر نیست.", entry
            )
        candidate = (model_dir / relative).resolve()
        if model_dir not in candidate.parents or not candidate.is_file():
            raise CheckpointError(
                f"یکی از فایل‌های مدل {spec.name} پیدا نشد.", str(candidate)
            )
        resolved.append(candidate)
    return tuple(resolved)


class ModelManager:
    """Keep at most one heavyweight ClearVoice instance in memory."""

    def __init__(
        self,
        checkpoints_root: Path,
        clearvoice_factory: Callable[[str, list[str], str], object],
        device: DeviceChoice,
        torch_module,
    ):
        self.checkpoints_root = Path(checkpoints_root)
        self.clearvoice_factory = clearvoice_factory
        self.preferred_device = device
        self.torch = torch_module
        self._model = None
        self._model_name: str | None = None
        self._device_name: str | None = None
        self._lock = threading.RLock()

    def _clear_cache(self, device_name: str | None) -> None:
        cache = getattr(self.torch, device_name or "", None)
        empty_cache = getattr(cache, "empty_cache", None)
        if callable(empty_cache):
            empty_cache()

    def release(self) -> None:
        with self._lock:
            previous_device = self._device_name
            self._model = None
            self._model_name = None
            self._device_name = None
            gc.collect()
            self._clear_cache(previous_device)

    def get(self, model_name: str, device_name: str | None = None):
        spec = get_model_spec(model_name)
        target_device = device_name or self.preferred_device.name
        validate_checkpoint(self.checkpoints_root, spec)
        with self._lock:
            if self._model_name == model_name and self._device_name == target_device:
                return self._model
            self.release()
            self._model = self.clearvoice_factory(spec.task, [spec.name], target_device)
            self._model_name = model_name
            self._device_name = target_device
            return self._model

    def run(self, model_name: str, input_path: str | Path, output_path: str | Path) -> str | None:
        with self._lock:
            model = self.get(model_name)
            try:
                model(
                    input_path=str(input_path),
                    online_write=True,
                    output_path=str(output_path),
                )
                return None
            except Exception as exc:
                if self._device_name != "mps" or not is_mps_fallback_error(exc):
                    raise
                self.release()
                clear_partial_outputs(output_path)
                cpu_model = self.get(model_name, "cpu")
                cpu_model(
                    input_path=str(input_path),
                    online_write=True,
                    output_path=str(output_path),
                )
                return "پردازش روی MPS پشتیبانی نشد و به‌صورت خودکار با CPU انجام شد."
