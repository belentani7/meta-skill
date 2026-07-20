"""Tests for meta-skill. Stdlib only: python -m unittest"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDX = json.loads((ROOT / "meta-skill" / "index.json").read_text(encoding="utf-8"))


def match(tier, model_id):
    return any(re.search(p, model_id, re.I) for p in IDX["alias_patterns"].get(tier, []))


class TestIndex(unittest.TestCase):
    def test_structure(self):
        for k in ("settings", "aliases", "alias_patterns", "tasks"):
            self.assertIn(k, IDX)

    def test_regexes_compile(self):
        for pats in IDX["alias_patterns"].values():
            for p in pats:
                re.compile(p, re.I)

    def test_budget_does_not_capture_gemini_pro(self):
        # regression: "mini" must never match "gemini"
        self.assertFalse(match("budget_fast", "google/gemini-3.0-pro"))
        self.assertTrue(match("budget_fast", "openai/gpt-5-mini"))
        self.assertTrue(match("budget_fast", "google/gemini-3.0-flash"))

    def test_premium_excludes_minis(self):
        self.assertTrue(match("premium_reasoning", "anthropic/claude-opus-5"))
        self.assertTrue(match("premium_reasoning", "google/gemini-3.0-pro"))
        self.assertFalse(match("premium_reasoning", "openai/gpt-5-mini"))

    def test_standard_excludes_minis(self):
        self.assertTrue(match("standard_coding", "anthropic/claude-sonnet-5"))
        self.assertFalse(match("standard_coding", "openai/gpt-4o-mini"))

    def test_local_tier_never_auto_updated(self):
        self.assertNotIn("local_zero_token", IDX["alias_patterns"])
        self.assertIn("local_zero_token", IDX["aliases"])

    def test_task_tiers_and_fallbacks_exist(self):
        for t in IDX["tasks"]:
            for tier in [t["tier"]] + t["fallback"]:
                self.assertIn(tier, IDX["aliases"], f"task {t['id']}")

    def test_task_ids_unique_with_keywords(self):
        ids = [t["id"] for t in IDX["tasks"]]
        self.assertEqual(len(ids), len(set(ids)))
        for t in IDX["tasks"]:
            self.assertTrue(t["keywords"], t["id"])

    def test_skill_frontmatter(self):
        text = (ROOT / "meta-skill" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: meta-skill", text)
        self.assertIn("description:", text)


class TestUpdater(unittest.TestCase):
    def test_validate_passes_on_shipped_index(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "upd", ROOT / "meta-skill" / "scripts" / "update_models.py")
        upd = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upd)
        self.assertEqual(upd.validate(IDX), [])
        self.assertEqual(upd.cost_per_1k({"pricing": {"prompt": "0.000003", "completion": "0.000015"}}), 0.018)
        self.assertEqual(upd.cost_per_1k({"pricing": {"prompt": "bad"}}), 0.0)
        self.assertTrue(upd.outputs_text({"architecture": {"modality": "text+image->text"}}))
        self.assertFalse(upd.outputs_text({"architecture": {"modality": "text->image"}}))


if __name__ == "__main__":
    unittest.main()
