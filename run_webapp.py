#!/usr/bin/env python3
"""Cross-platform local entry point for the Persian ClearVoice UI."""

from __future__ import annotations

import importlib
import os
import shutil
import sys
import threading
import webbrowser
from contextlib import contextmanager
from pathlib import Path


_CWD_LOCK = threading.RLock()


def resolve_repository_root() -> Path:
    return Path(__file__).resolve().parent


@contextmanager
def repository_working_directory(root: Path):
    """Keep upstream relative checkpoint/config paths anchored to the repo."""
    with _CWD_LOCK:
        previous = Path.cwd()
        os.chdir(root)
        try:
            yield
        finally:
            os.chdir(previous)


def load_clearvoice_api(repository_root: Path):
    """Load either the legacy flat layout or the newer package layout."""

    package_root = repository_root / "clearvoice"
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))
    clearvoice_module = importlib.import_module("clearvoice")
    clearvoice_class = clearvoice_module.ClearVoice
    try:
        networks = importlib.import_module("clearvoice.networks")
    except ModuleNotFoundError:
        networks = importlib.import_module("networks")
    return clearvoice_class, networks


def configure_legacy_paths(repository_root: Path, wrapper_class) -> None:
    """Adapt the legacy flat source tree without editing upstream files."""

    marker = "_persian_webapp_paths_configured"
    if getattr(wrapper_class, marker, False):
        return
    source_root = repository_root / "clearvoice"
    for method_name in ("load_args_se", "load_args_ss", "load_args_sr", "load_args_tse"):
        original = getattr(wrapper_class, method_name, None)
        if not callable(original):
            continue

        def load_with_local_config(self, *args, _original=original, **kwargs):
            with repository_working_directory(source_root):
                result = _original(self, *args, **kwargs)
            if getattr(self, "args", None) is not None and getattr(self, "model_name", None):
                self.args.checkpoint_dir = str(
                    repository_root / "checkpoints" / self.model_name
                )
            return result

        setattr(wrapper_class, method_name, load_with_local_config)
    setattr(wrapper_class, marker, True)


def _block_network_downloads(networks):
    """Disable upstream checkpoint downloads without requiring source edits."""
    def offline_only(self, model_name):
        raise FileNotFoundError(
            f"Local checkpoint for {model_name} is missing; automatic download is disabled."
        )

    networks.SpeechModel.download_model = offline_only


def build_clearvoice_factory(repository_root: Path, torch_module):
    ClearVoice, networks = load_clearvoice_api(repository_root)
    if (repository_root / "clearvoice" / "clearvoice.py").is_file():
        clearvoice_module = sys.modules.get(ClearVoice.__module__)
        legacy_wrapper = getattr(clearvoice_module, "network_wrapper", None)
        if legacy_wrapper is not None:
            configure_legacy_paths(repository_root, legacy_wrapper)
    _block_network_downloads(networks)

    def factory(task: str, model_names: list[str], device_name: str):
        with repository_working_directory(repository_root):
            instance = ClearVoice(task=task, model_names=model_names)
        device = torch_module.device(device_name)
        for wrapper in instance.models:
            wrapper.device = device
            wrapper.args.use_cuda = 1 if device_name == "cuda" else 0
            wrapper.args.checkpoint_dir = str(repository_root / "checkpoints" / wrapper.name)
            wrapper.model.to(device)
            wrapper.model.eval()
        return instance

    return factory


def main() -> int:
    root = resolve_repository_root()
    try:
        import torch
        from webapp.app import create_app
        from webapp.config import AppConfig
        from webapp.diagnostics import run_diagnostics
        from webapp.model_manager import ModelManager
        from webapp.processing import ProcessingService
        from webapp.storage import JobStore
    except ImportError as exc:
        print("\nوابستگی‌های برنامه کامل نیستند.")
        print("ابتدا راهنمای WEBAPP_GUIDE_FA.md را اجرا کنید.")
        print(f"جزئیات فنی: {exc}\n")
        return 2

    config = AppConfig.discover(root)
    ffmpeg_path = shutil.which("ffmpeg")
    report = run_diagnostics(config, torch, ffmpeg_path)
    if report.fatal_errors:
        print("\nبرنامه به دلیل مشکلات زیر اجرا نشد:")
        for item in report.fatal_errors:
            print(f"- {item}")
        return 2

    store = JobStore(config.runtime_root)
    factory = build_clearvoice_factory(root, torch)
    manager = ModelManager(config.checkpoints_root, factory, report.device, torch)
    service = ProcessingService(
        store, manager, report.ffmpeg_available, config.max_upload_bytes
    )
    app = create_app(config, service, store, report.as_dict())
    port = int(os.getenv("CLEARVOICE_PORT", "5000"))
    address = f"http://127.0.0.1:{port}"
    print(f"\nClearVoice آماده است: {address}")
    if os.getenv("CLEARVOICE_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(address)).start()
    app.run(
        host="127.0.0.1", port=port, debug=False,
        threaded=False, use_reloader=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
