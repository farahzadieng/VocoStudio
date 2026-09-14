import importlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EntrypointTests(unittest.TestCase):
    def test_entrypoint_import_does_not_start_server(self):
        module = importlib.import_module("run_webapp")
        self.assertEqual(module.resolve_repository_root(), ROOT)

    def test_server_is_loopback_only(self):
        text = (ROOT / "run_webapp.py").read_text(encoding="utf-8")
        self.assertIn('host="127.0.0.1"', text)
        self.assertIn("use_reloader=False", text)

    def test_macos_launcher_resolves_own_directory(self):
        text = (ROOT / "start_webapp.command").read_text(encoding="utf-8")
        self.assertIn('dirname "$0"', text)
        self.assertIn("run_webapp.py", text)

    def test_windows_launcher_resolves_own_directory(self):
        text = (ROOT / "start_webapp.bat").read_text(encoding="utf-8")
        self.assertIn("%~dp0", text)
        self.assertIn("run_webapp.py", text)
        self.assertIn("chcp 65001", text)

    def test_requirements_install_runtime_dependencies_without_editable_package(self):
        lines = [line.strip() for line in (ROOT / "requirements-webapp.txt").read_text().splitlines() if line.strip()]
        self.assertIn("Flask>=3.0,<4.0", lines)
        self.assertTrue(any(line.startswith("torch") for line in lines))
        self.assertNotIn("-e ./clearvoice", lines)

    def test_flat_legacy_clearvoice_layout_can_be_loaded(self):
        module = importlib.import_module("run_webapp")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "clearvoice"
            source.mkdir()
            (source / "clearvoice.py").write_text("class ClearVoice: pass\n", encoding="utf-8")
            (source / "networks.py").write_text(
                "class SpeechModel:\n    def download_model(self, name): return True\n",
                encoding="utf-8",
            )
            saved = {name: sys.modules.pop(name, None) for name in ("clearvoice", "networks")}
            old_path = list(sys.path)
            try:
                clearvoice_class, networks = module.load_clearvoice_api(root)
                self.assertEqual(clearvoice_class.__name__, "ClearVoice")
                self.assertTrue(hasattr(networks, "SpeechModel"))
            finally:
                sys.path[:] = old_path
                for name in ("clearvoice", "networks"):
                    sys.modules.pop(name, None)
                    if saved[name] is not None:
                        sys.modules[name] = saved[name]

    def test_macos_installer_creates_venv_and_installs_inference_package(self):
        text = (ROOT / "install_webapp.command").read_text(encoding="utf-8")
        self.assertIn("-m venv .venv", text)
        self.assertIn("pip install -r requirements-webapp.txt", text)
        self.assertNotIn("-e ./clearvoice -r", text)
        self.assertNotIn('clearvoice/clearvoice', text)

    def test_windows_installer_creates_venv_and_installs_inference_package(self):
        text = (ROOT / "install_webapp.bat").read_text(encoding="utf-8")
        self.assertIn("chcp 65001", text)
        self.assertIn("-m venv .venv", text)
        self.assertIn("pip install -r requirements-webapp.txt", text)
        self.assertNotIn("-e ./clearvoice -r", text)
        self.assertNotIn('clearvoice\\clearvoice', text)


if __name__ == "__main__":
    unittest.main()
