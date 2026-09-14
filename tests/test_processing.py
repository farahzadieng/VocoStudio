import io
import tempfile
import unittest
from pathlib import Path

from webapp.errors import MediaValidationError, ProcessingError
from webapp.processing import ProcessingService
from webapp.storage import JobStore


class Upload:
    filename = "sample.wav"

    def __init__(self):
        self.stream = io.BytesIO(b"RIFF\x00\x00\x00\x00WAVEfmt ")


class FakeManager:
    def __init__(self):
        self.calls = []

    def run(self, model_name, input_path, output_path):
        self.calls.append((model_name, Path(input_path), Path(output_path)))
        output = Path(output_path) / model_name
        output.mkdir(parents=True)
        if model_name == "MossFormer2_SS_16K":
            (output / "mix_s1.wav").write_bytes(b"one")
            (output / "mix_s2.wav").write_bytes(b"two")
        else:
            (output / "result.wav").write_bytes(b"audio")
        return None


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.manager = FakeManager()
        self.store = JobStore(Path(self.temp.name))
        self.service = ProcessingService(self.store, self.manager, False, 1024)

    def tearDown(self):
        self.temp.cleanup()

    def test_enhancement_requires_valid_explicit_model(self):
        with self.assertRaises(MediaValidationError):
            self.service.process("enhancement", "MossFormer2_SS_16K", Upload())

    def test_fixed_tool_uses_its_only_model(self):
        result = self.service.process("separation", None, Upload())
        self.assertEqual(result.model_name, "MossFormer2_SS_16K")
        self.assertEqual([item.label_fa for item in result.outputs], ["گوینده اول", "گوینده دوم"])
        self.assertIsNotNone(result.bundle_name)

    def test_empty_outputs_are_reported(self):
        self.manager.run = lambda *args: None
        with self.assertRaisesRegex(ProcessingError, "خروجی"):
            self.service.process("enhancement", "FRCRN_SE_16K", Upload())


if __name__ == "__main__":
    unittest.main()
