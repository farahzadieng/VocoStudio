import unittest
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OfflinePatchTests(unittest.TestCase):
    def test_patch_removes_huggingface_download_fallback(self):
        text = (ROOT / "patches/clearvoice-local-checkpoints.patch").read_text(encoding="utf-8")
        self.assertIn("automatic download is disabled", text)
        self.assertIn("-        from huggingface_hub import snapshot_download", text)
        self.assertIn("-            snapshot_download", text)

    def test_runtime_also_blocks_download_without_applying_patch(self):
        text = (ROOT / "run_webapp.py").read_text(encoding="utf-8")
        self.assertIn("SpeechModel.download_model = offline_only", text)

    def test_patch_is_structurally_applicable(self):
        result = subprocess.run(
            ["git", "apply", "--check", "--directory=tests/patch-fixture", "patches/clearvoice-local-checkpoints.patch"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
