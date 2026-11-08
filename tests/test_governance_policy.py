"""Constitution gate regression tests."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("governance_policy", ROOT / "governance" / "policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class GovernanceTests(unittest.TestCase):
    def test_safe_proposal(self):
        self.assertEqual([], policy.assess({"action": "propose_patch", "environment": "sandbox", "paths": ["src/feature.py"]}))

    def test_production_is_denied(self):
        self.assertTrue(policy.assess({"action": "open_pr", "environment": "production", "paths": ["src/a.py"]}))

    def test_direct_merge_denied(self):
        self.assertTrue(policy.assess({"action": "merge", "environment": "none", "paths": []}))

    def test_protected_constitution_denied(self):
        self.assertTrue(policy.assess({"action": "propose_patch", "environment": "sandbox", "paths": ["governance/CONSTITUTION.md"]}))

    def test_workflow_denied(self):
        self.assertTrue(policy.assess({"action": "propose_patch", "environment": "sandbox", "paths": [".github/workflows/ci.yml"]}))

    def test_traversal_denied(self):
        self.assertTrue(policy.assess({"action": "propose_patch", "environment": "sandbox", "paths": ["src/../governance/policy.py"]}))

    def test_empty_paths_denied(self):
        self.assertTrue(policy.assess({"action": "propose_patch", "environment": "sandbox", "paths": []}))

    def test_unknown_action_denied(self):
        self.assertTrue(policy.assess({"action": "deploy", "environment": "none", "paths": []}))

    def test_invalid_input_denied(self):
        self.assertTrue(policy.assess({"action": "observe", "environment": "none", "paths": "src"}))


if __name__ == "__main__":
    unittest.main()
