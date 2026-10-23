import unittest
from news_reporter.security_runtime import patched_certifi


class SecurityRuntimeTests(unittest.TestCase):
    def test_rejects_old_certificate_bundle(self):
        self.assertFalse(patched_certifi('2026.10.18'))

    def test_accepts_patched_and_newer_bundles(self):
        self.assertTrue(patched_certifi('2026.10.19'))
        self.assertTrue(patched_certifi('2027.1.1'))
