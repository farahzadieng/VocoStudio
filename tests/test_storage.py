import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from webapp.storage import JobStore


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = JobStore(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_output_resolution_rejects_traversal(self):
        job = self.store.create()
        output = job.output_dir / "speaker-1.wav"
        output.write_bytes(b"audio")
        self.store.register_outputs(job.id, [output])
        self.assertEqual(self.store.resolve_output(job.id, "speaker-1.wav"), output)
        with self.assertRaises(KeyError):
            self.store.resolve_output(job.id, "../speaker-1.wav")

    def test_bundle_contains_only_registered_outputs(self):
        job = self.store.create()
        first = job.output_dir / "speaker-1.wav"
        second = job.output_dir / "speaker-2.wav"
        ignored = job.output_dir / "debug.log"
        for path in (first, second, ignored):
            path.write_bytes(path.name.encode())
        self.store.register_outputs(job.id, [first, second])
        bundle = self.store.bundle_outputs(job.id)
        with zipfile.ZipFile(bundle) as archive:
            self.assertEqual(archive.namelist(), ["speaker-1.wav", "speaker-2.wav"])

    def test_saved_upload_uses_generated_name(self):
        import io
        job = self.store.create()
        saved = self.store.save_upload(job, io.BytesIO(b"data"), "../../voice.wav")
        self.assertEqual(saved.parent, job.input_dir)
        self.assertEqual(saved.suffix, ".wav")
        self.assertNotIn("voice", saved.name)

    def test_stale_cleanup_does_not_touch_new_jobs(self):
        old = self.store.create()
        fresh = self.store.create()
        stale_time = time.time() - 48 * 3600
        import os
        os.utime(old.root, (stale_time, stale_time))
        removed = self.store.cleanup_stale(24)
        self.assertIn(old.id, removed)
        self.assertTrue(fresh.root.exists())

