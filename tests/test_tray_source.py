import re
import unittest
from pathlib import Path


class TrayRecoverySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "tray.py").read_text(encoding="utf-8")

    def test_health_check_verifies_helper_identity(self):
        self.assertIn('HEALTH_SERVICE_NAME = "gofile-abdm-helper"', self.source)
        self.assertIn('payload = json.load(response)', self.source)
        self.assertIn('payload.get("ok") is True', self.source)
        self.assertIn('payload.get("service") == HEALTH_SERVICE_NAME', self.source)

    def test_owned_hung_helper_restarts_only_after_repeated_failures(self):
        match = re.search(r"HEALTH_FAILURE_RESTART_THRESHOLD\s*=\s*(\d+)", self.source)
        self.assertIsNotNone(match)
        self.assertGreaterEqual(int(match.group(1)), 3)
        start = self.source.index("def _monitor()")
        end = self.source.index("def _create_icon_image()", start)
        block = self.source[start:end]
        self.assertIn("consecutive_owned_health_failures += 1", block)
        self.assertIn("HEALTH_FAILURE_RESTART_THRESHOLD", block)
        self.assertIn("_stop_owned_helper()", block)
        self.assertIn("_start_helper()", block)


if __name__ == "__main__":
    unittest.main()
