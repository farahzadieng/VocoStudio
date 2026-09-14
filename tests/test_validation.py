import io
import unittest

from webapp.errors import MediaValidationError
from webapp.model_catalog import get_tool_spec
from webapp.validation import validate_upload


class Upload:
    def __init__(self, filename, data):
        self.filename = filename
        self.stream = io.BytesIO(data)


class ValidationTests(unittest.TestCase):
    def test_wav_is_allowed_without_ffmpeg(self):
        result = validate_upload(
            Upload("voice.wav", b"RIFF\x00\x00\x00\x00WAVEfmt "),
            get_tool_spec("enhancement"), False, 100,
        )
        self.assertEqual(result.extension, ".wav")

    def test_mp3_requires_ffmpeg(self):
        with self.assertRaisesRegex(MediaValidationError, "FFmpeg"):
            validate_upload(
                Upload("voice.mp3", b"ID3audio"),
                get_tool_spec("enhancement"), False, 100,
            )

    def test_video_is_rejected_by_audio_tool(self):
        with self.assertRaises(MediaValidationError):
            validate_upload(
                Upload("clip.mp4", b"\x00\x00\x00\x18ftypmp42"),
                get_tool_spec("enhancement"), True, 100,
            )

    def test_upload_limit_is_enforced(self):
        with self.assertRaisesRegex(MediaValidationError, "حجم"):
            validate_upload(
                Upload("voice.wav", b"RIFF" + b"x" * 100),
                get_tool_spec("enhancement"), False, 20,
            )

    def test_fake_wav_is_rejected(self):
        with self.assertRaisesRegex(MediaValidationError, "ساختار"):
            validate_upload(
                Upload("voice.wav", b"not a wave"),
                get_tool_spec("enhancement"), False, 100,
            )

