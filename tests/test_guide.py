import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GuideTests(unittest.TestCase):
    def test_guide_explains_exact_placement_and_both_systems(self):
        text = (ROOT / "WEBAPP_GUIDE_FA.md").read_text(encoding="utf-8")
        for phrase in (
            "کنار پوشه `checkpoints`", "macOS", "Windows",
            "install_webapp.command", "install_webapp.bat",
            "start_webapp.command", "start_webapp.bat",
        ):
            self.assertIn(phrase, text)

    def test_guide_states_original_files_need_no_mandatory_change(self):
        text = (ROOT / "WEBAPP_GUIDE_FA.md").read_text(encoding="utf-8")
        self.assertIn("هیچ تغییر اجباری", text)
        self.assertIn("clearvoice-local-checkpoints.patch", text)

    def test_guide_documents_device_override_and_tests(self):
        text = (ROOT / "WEBAPP_GUIDE_FA.md").read_text(encoding="utf-8")
        self.assertIn("CLEARVOICE_DEVICE", text)
        self.assertIn("unittest discover", text)

    def test_guide_documents_two_command_uv_setup(self):
        text = (ROOT / "WEBAPP_GUIDE_FA.md").read_text(encoding="utf-8")
        self.assertIn("uv pip install -r requirements-webapp.txt", text)
        self.assertIn("uv run python run_webapp.py", text)


if __name__ == "__main__":
    unittest.main()
