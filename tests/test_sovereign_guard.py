import importlib.util
import pathlib
import unittest

path = pathlib.Path(__file__).resolve().parents[1] / "sovereign" / "guard.py"
spec = importlib.util.spec_from_file_location("sovereign_guard", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ConstitutionalGuardTests(unittest.TestCase):
    def setUp(self):
        self.action = dict(type="propose_patch", repository="belentani7/meta-skill",
                           branch="feat/example", paths=["src/example.py"],
                           estimated_cost_usd=0, tests_passed=True)
    def test_safe_proposal(self):
        self.assertTrue(mod.evaluate(self.action, ["belentani7/meta-skill"])["allowed"])
    def test_unknown_repository(self):
        self.assertFalse(mod.evaluate(self.action, [])["allowed"])
    def test_protected_branch(self):
        self.action["branch"] = "main"
        self.assertFalse(mod.evaluate(self.action, ["belentani7/meta-skill"])["allowed"])
    def test_secret_path(self):
        self.action["paths"] = [".env"]
        self.assertFalse(mod.evaluate(self.action, ["belentani7/meta-skill"])["allowed"])
    def test_tests_missing(self):
        self.action["tests_passed"] = False
        self.assertFalse(mod.evaluate(self.action, ["belentani7/meta-skill"])["allowed"])
    def test_missing_cost(self):
        del self.action["estimated_cost_usd"]
        self.assertFalse(mod.evaluate(self.action, ["belentani7/meta-skill"])["allowed"])
    def test_unknown_action(self):
        self.action["type"] = "deploy"
        self.assertFalse(mod.evaluate(self.action, ["belentani7/meta-skill"])["allowed"])

if __name__ == "__main__":
    unittest.main()
