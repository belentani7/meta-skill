"""Regression tests for read-only GitHub fleet inventory pagination."""

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "github_repo_health.py"
spec = importlib.util.spec_from_file_location("github_repo_health", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
inventory = module.inventory


class InventoryPaginationTests(unittest.TestCase):
    def test_mixed_owner_pages_do_not_stop_early(self):
        ours = lambda n: {"full_name": f"belentani7/repo-{n}", "owner": {"login": "belentani7"}}
        other = {"full_name": "other/example", "owner": {"login": "other"}}
        pages = [
            [ours(i) for i in range(99)] + [other],
            [ours(i) for i in range(99, 199)] ,
            [ours(199)],
        ]
        with patch.object(module, "get", side_effect=pages) as api:
            records = inventory("belentani7", "synthetic-test-token", 0)
        self.assertEqual(len(records), 200)
        self.assertEqual(api.call_count, 3)
        self.assertTrue(all(r["owner"]["login"] == "belentani7" for r in records))

    def test_result_limit_is_respected(self):
        one_page = [{"full_name": f"belentani7/r{i}", "owner": {"login": "belentani7"}} for i in range(100)]
        with patch.object(module, "get", return_value=one_page) as api:
            records = inventory("belentani7", "synthetic-test-token", 5)
        self.assertEqual(len(records), 5)
        self.assertEqual(api.call_count, 1)

    def test_invalid_api_shape_fails_closed(self):
        with patch.object(module, "get", return_value={"message": "error"}):
            with self.assertRaises(ValueError):
                inventory("belentani7", "synthetic-test-token", 0)


if __name__ == "__main__":
    unittest.main()
