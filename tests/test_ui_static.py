import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StaticUiTests(unittest.TestCase):
    def test_base_is_persian_rtl_and_offline(self):
        text = (ROOT / "webapp/templates/base.html").read_text(encoding="utf-8")
        self.assertIn('lang="fa"', text)
        self.assertIn('dir="rtl"', text)
        self.assertNotIn("https://", text)
        self.assertNotIn("http://", text)

    def test_dashboard_names_all_four_tools(self):
        text = (ROOT / "webapp/templates/index.html").read_text(encoding="utf-8")
        for phrase in (
            "بهبود کیفیت صدا", "جداسازی دو گوینده",
            "افزایش وضوح صدا", "استخراج گوینده هدف",
        ):
            self.assertIn(phrase, text)

    def test_tool_form_supports_drop_and_csrf(self):
        text = (ROOT / "webapp/templates/tool.html").read_text(encoding="utf-8")
        self.assertIn('class="drop-zone"', text)
        self.assertIn('name="csrf_token"', text)
        self.assertIn('name="media"', text)

    def test_result_has_preview_and_download(self):
        text = (ROOT / "webapp/templates/result.html").read_text(encoding="utf-8")
        self.assertIn("<audio", text)
        self.assertIn("<video", text)
        self.assertIn("دانلود", text)
        self.assertNotIn(" }} }}", text)

    def test_css_has_focus_and_reduced_motion(self):
        text = (ROOT / "webapp/static/css/app.css").read_text(encoding="utf-8")
        self.assertIn(":focus-visible", text)
        self.assertIn("prefers-reduced-motion", text)

    def test_javascript_handles_drop_and_duplicate_submit(self):
        text = (ROOT / "webapp/static/js/app.js").read_text(encoding="utf-8")
        self.assertIn('addEventListener("drop"', text)
        self.assertIn("button.disabled = true", text)


if __name__ == "__main__":
    unittest.main()
