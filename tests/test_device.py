from types import SimpleNamespace

import unittest

from webapp.device import choose_device, is_mps_fallback_error


class FakeTorch:
    def __init__(self, cuda=False, mps=False, built=False):
        self.cuda = SimpleNamespace(is_available=lambda: cuda)
        self.backends = SimpleNamespace(
            mps=SimpleNamespace(
                is_available=lambda: mps,
                is_built=lambda: built,
            )
        )

    @staticmethod
    def device(name):
        return name


class DeviceTests(unittest.TestCase):
    def test_auto_device_order(self):
        cases = [
            (FakeTorch(cuda=True, mps=True, built=True), "cuda"),
            (FakeTorch(mps=True, built=True), "mps"),
            (FakeTorch(), "cpu"),
        ]
        for fake, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(choose_device(fake).name, expected)

    def test_explicit_cpu_is_always_available(self):
        self.assertEqual(choose_device(FakeTorch(cuda=True), "cpu").name, "cpu")

    def test_unavailable_explicit_device_has_persian_error(self):
        with self.assertRaisesRegex(ValueError, "در دسترس نیست"):
            choose_device(FakeTorch(), "cuda")

    def test_only_backend_errors_trigger_mps_fallback(self):
        self.assertTrue(is_mps_fallback_error(RuntimeError("not implemented for MPS")))
        self.assertTrue(is_mps_fallback_error(RuntimeError("Metal backend does not support operation")))
        self.assertFalse(is_mps_fallback_error(ValueError("bad input")))
