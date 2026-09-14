import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from webapp.device import DeviceChoice
from webapp.errors import CheckpointError
from webapp.model_catalog import MODEL_CATALOG, get_model_spec
from webapp.model_manager import ModelManager, validate_checkpoint


def make_checkpoint(root: Path, name: str, entries=("weights.pt",)) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "last_best_checkpoint").write_text("\n".join(entries) + "\n")
    for entry in entries:
        (directory / entry).write_bytes(b"checkpoint")
    return directory


class FakeTorch:
    def __init__(self):
        self.cuda = SimpleNamespace(empty_cache=lambda: None)
        self.mps = SimpleNamespace(empty_cache=lambda: None)


class ModelManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_validates_manifest_references(self):
        make_checkpoint(self.root, "MossFormer2_SR_48K", ("moss.pt", "generator.pt"))
        paths = validate_checkpoint(self.root, get_model_spec("MossFormer2_SR_48K"))
        self.assertEqual([path.name for path in paths], ["moss.pt", "generator.pt"])

    def test_missing_referenced_file_has_model_name(self):
        directory = self.root / "FRCRN_SE_16K"
        directory.mkdir()
        (directory / "last_best_checkpoint").write_text("missing.pt\n")
        with self.assertRaisesRegex(CheckpointError, "FRCRN_SE_16K"):
            validate_checkpoint(self.root, get_model_spec("FRCRN_SE_16K"))

    def test_manifest_rejects_path_traversal(self):
        directory = self.root / "FRCRN_SE_16K"
        directory.mkdir()
        (directory / "last_best_checkpoint").write_text("../outside.pt\n")
        (self.root / "outside.pt").write_bytes(b"bad")
        with self.assertRaises(CheckpointError):
            validate_checkpoint(self.root, get_model_spec("FRCRN_SE_16K"))

    def test_manager_reuses_same_model_and_releases_previous(self):
        for name in ("FRCRN_SE_16K", "MossFormer2_SE_48K"):
            make_checkpoint(self.root, name)
        created = []

        class FakeModel:
            def __init__(self, task, names, device):
                self.task, self.names, self.device = task, names, device

        def factory(task, model_names, device):
            created.append((task, tuple(model_names), device))
            return FakeModel(task, tuple(model_names), device)

        manager = ModelManager(
            self.root, factory, DeviceChoice("cpu", "CPU"), FakeTorch()
        )
        first = manager.get("FRCRN_SE_16K")
        self.assertIs(manager.get("FRCRN_SE_16K"), first)
        manager.get("MossFormer2_SE_48K")
        self.assertEqual([item[1][0] for item in created], [
            "FRCRN_SE_16K", "MossFormer2_SE_48K"
        ])

    def test_mps_backend_failure_retries_once_on_cpu(self):
        make_checkpoint(self.root, "FRCRN_SE_16K")
        attempts = []

        class FakeModel:
            def __init__(self, device):
                self.device = device

            def __call__(self, input_path, online_write, output_path):
                attempts.append(self.device)
                if self.device == "mps":
                    Path(output_path).mkdir(parents=True, exist_ok=True)
                    (Path(output_path) / "partial.wav").write_bytes(b"partial")
                    raise RuntimeError("operation not implemented for MPS backend")
                Path(output_path).mkdir(parents=True, exist_ok=True)
                (Path(output_path) / "result.wav").write_bytes(b"ok")

        manager = ModelManager(
            self.root,
            lambda task, model_names, device: FakeModel(device),
            DeviceChoice("mps", "MPS"), FakeTorch(),
        )
        notice = manager.run("FRCRN_SE_16K", "input.wav", self.root / "out")
        self.assertEqual(attempts, ["mps", "cpu"])
        self.assertIn("CPU", notice)
        self.assertFalse((self.root / "out" / "partial.wav").exists())

    def test_non_mps_failure_is_not_retried(self):
        make_checkpoint(self.root, "FRCRN_SE_16K")
        calls = []

        class Broken:
            def __call__(self, *args, **kwargs):
                calls.append(1)
                raise ValueError("invalid media")

        manager = ModelManager(
            self.root,
            lambda task, model_names, device: Broken(),
            DeviceChoice("mps", "MPS"), FakeTorch(),
        )
        with self.assertRaisesRegex(ValueError, "invalid media"):
            manager.run("FRCRN_SE_16K", "input.wav", self.root / "out")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
