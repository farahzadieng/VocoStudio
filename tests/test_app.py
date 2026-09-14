import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


FLASK_AVAILABLE = importlib.util.find_spec("flask") is not None


@unittest.skipUnless(FLASK_AVAILABLE, "Flask is installed by requirements-webapp.txt")
class AppRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from webapp.app import create_app
        from webapp.config import AppConfig
        from webapp.storage import JobStore

        cls.temp = tempfile.TemporaryDirectory()
        root = Path(cls.temp.name)
        cls.store = JobStore(root / "runtime")

        class FakeService:
            def process(self, tool_slug, model_name, upload):
                from webapp.processing import JobResult, OutputArtifact
                job = cls.store.create()
                output = job.output_dir / "result.wav"
                output.write_bytes(b"audio")
                cls.store.register_outputs(job.id, [output])
                result = JobResult(
                    job.id, tool_slug, "بهبود کیفیت صدا", model_name,
                    "مدل سریع و سبک", upload.filename, 5,
                    (OutputArtifact("result.wav", "صدای پردازش‌شده", "audio"),),
                    None, None,
                )
                cls.store.update_result(job.id, {
                    "tool_slug": result.tool_slug, "tool_title_fa": result.tool_title_fa,
                    "model_name": result.model_name, "model_label_fa": result.model_label_fa,
                    "input_name": result.input_name, "input_size": 5,
                    "artifacts": [{"filename": "result.wav", "label_fa": "صدای پردازش‌شده", "media_kind": "audio"}],
                    "bundle_name": None, "notice_fa": None,
                })
                return result

            def load_result(self, job_id):
                from webapp.processing import JobResult, OutputArtifact
                data = cls.store.read_metadata(job_id)
                return JobResult(
                    job_id, data["tool_slug"], data["tool_title_fa"], data["model_name"],
                    data["model_label_fa"], data["input_name"], data["input_size"],
                    tuple(OutputArtifact(**item) for item in data["artifacts"]), None, None,
                )

        config = AppConfig(root, root / "checkpoints", root / "runtime")
        app = create_app(config, FakeService(), cls.store, {"device": "CPU", "models_ready": 6})
        app.config.update(TESTING=True, SECRET_KEY="test")
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_dashboard_is_persian_rtl(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('dir="rtl"', response.get_data(as_text=True))

    def test_all_tool_pages_exist(self):
        for slug in ("enhancement", "separation", "super-resolution", "target-speaker"):
            self.assertEqual(self.client.get(f"/tools/{slug}").status_code, 200)

    def test_process_redirects_to_result(self):
        page = self.client.get("/tools/enhancement").get_data(as_text=True)
        import re
        token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
        response = self.client.post(
            "/process/enhancement",
            data={
                "csrf_token": token,
                "model_name": "FRCRN_SE_16K",
                "media": (io.BytesIO(b"RIFF\x00\x00\x00\x00WAVE"), "voice.wav"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 303)
        self.assertIn("/results/", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
