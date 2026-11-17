import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "sovereign"
import sys
sys.path.insert(0, str(ROOT))
from executor import prepare

class ExecutorTests(unittest.TestCase):
    def test_rejects_unknown_repo(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "inventory.json"
            p.write_text(json.dumps({"repositories": []}))
            with self.assertRaises(PermissionError):
                prepare({"type": "read", "repository": "unknown", "estimated_cost_usd": 0}, p)
    def test_safe_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "inventory.json"
            p.write_text(json.dumps({"repositories": [{"name": "owner/repo", "archived": False}]}))
            self.assertEqual(prepare({"type": "read", "repository": "owner/repo", "estimated_cost_usd": 0}, p)["status"], "authorized_for_external_executor")
if __name__ == "__main__":
    unittest.main()
