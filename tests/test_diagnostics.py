import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from webapp.config import AppConfig
from webapp.diagnostics import run_diagnostics
from webapp.model_catalog import MODEL_CATALOG


def populate_checkpoints(root: Path):
    for name in MODEL_CATALOG:
        directory = root / name
        directory.mkdir(parents=True)
        (directory / "last_best_checkpoint").write_text("weights.pt\n")
        (directory / "weights.pt").write_bytes(b"weights")


class FakeTorch:
    cuda = SimpleNamespace(is_available=lambda: False)
    backends = SimpleNamespace(
        mps=SimpleNamespace(is_available=lambda: False, is_built=lambda: False)
    )


class DiagnosticsTests(unittest.TestCase):
    def test_complete_local_setup_reports_six_models(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "clearvoice" / "clearvoice").mkdir(parents=True)
            populate_checkpoints(root / "checkpoints")
            config = AppConfig.discover(root)
            report = run_diagnostics(config, FakeTorch(), ffmpeg_path="/usr/bin/ffmpeg")
            self.assertEqual(report.models_ready, 6)
            self.assertEqual(report.device.name, "cpu")
            self.assertEqual(report.unavailable_models, ())

    def test_partial_models_do_not_make_dashboard_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "clearvoice" / "clearvoice").mkdir(parents=True)
            config = AppConfig.discover(root)
            report = run_diagnostics(config, FakeTorch(), ffmpeg_path=None)
            self.assertEqual(report.models_ready, 0)
            self.assertEqual(len(report.unavailable_models), 6)
            self.assertFalse(report.ffmpeg_available)

    def test_top_level_clearvoice_directory_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "clearvoice").mkdir()
            populate_checkpoints(root / "checkpoints")
            config = AppConfig.discover(root)
            report = run_diagnostics(config, FakeTorch(), ffmpeg_path="/usr/bin/ffmpeg")
            self.assertEqual(report.fatal_errors, ())

    def test_missing_clearvoice_source_is_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            config = AppConfig.discover(Path(temp))
            report = run_diagnostics(config, FakeTorch(), ffmpeg_path=None)
            self.assertTrue(report.fatal_errors)


if __name__ == "__main__":
    unittest.main()
