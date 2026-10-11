"""Data and model-catalog updater tests. Standard library only."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "meta-skill" / "index.json"
IDX = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
UPDATER_PATH = ROOT / "meta-skill" / "scripts" / "update_models.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UPDATER = load_module("meta_skill_update_models", UPDATER_PATH)


class TestIndex(unittest.TestCase):
    def test_required_sections_and_router_settings(self):
        for key in ("settings", "aliases", "alias_patterns", "tasks"):
            self.assertIn(key, IDX)
        self.assertIn("default_tier", IDX["settings"])
        self.assertIn("minimum_route_confidence", IDX["settings"])
        self.assertGreater(IDX["settings"]["token_budget_per_task"], 0)

    def test_regexes_compile(self):
        for patterns in IDX["alias_patterns"].values():
            for pattern in patterns:
                __import__("re").compile(pattern, __import__("re").I)

    def test_budget_aliases_do_not_capture_other_model_families(self):
        import re
        matches = lambda tier, model_id: any(
            re.search(pattern, model_id, re.I)
            for pattern in IDX["alias_patterns"].get(tier, [])
        )
        self.assertFalse(matches("budget_fast", "google/gemini-3.0-pro"))
        self.assertTrue(matches("budget_fast", "openai/gpt-5-mini"))
        self.assertTrue(matches("budget_fast", "google/gemini-3.0-flash"))
        self.assertFalse(matches("premium_reasoning", "openai/gpt-5-mini"))

    def test_local_zero_token_is_never_a_catalog_pattern(self):
        self.assertNotIn("local_zero_token", IDX["alias_patterns"])
        self.assertIn("local_zero_token", IDX["aliases"])
        self.assertIn("without a model call", IDX["aliases"]["local_zero_token"])

    def test_tasks_reference_existing_tiers_and_are_complete(self):
        task_ids = [task["id"] for task in IDX["tasks"]]
        self.assertEqual(len(task_ids), len(set(task_ids)))
        self.assertGreaterEqual(len(task_ids), 12)
        for task in IDX["tasks"]:
            self.assertTrue(task["keywords"], task["id"])
            self.assertTrue(task["directive"], task["id"])
            for tier in [task["tier"]] + task["fallback"]:
                self.assertIn(tier, IDX["aliases"], task["id"])

    def test_skill_frontmatter(self):
        text = (ROOT / "meta-skill" / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("name: meta-skill", text)
        self.assertIn("description:", text)

    def test_magic_markdown_is_valid_utf8_text_without_mojibake(self):
        for filename in ("magic/ai-instructions.md", "magic/lore.md"):
            text = (ROOT / filename).read_text(encoding="utf-8")
            self.assertFalse(text.startswith("\ufeff"), filename)
            self.assertNotIn("Â", text, filename)
            self.assertNotIn("â", text, filename)


class TestUpdater(unittest.TestCase):
    def test_shipped_index_validates(self):
        self.assertEqual(UPDATER.validate(IDX), [])

    def test_costs_keep_prompt_and_completion_rates_separate(self):
        model = {"pricing": {"prompt": "0.000003", "completion": "0.000015"}}
        self.assertEqual(UPDATER.pricing_per_1k(model), (0.003, 0.015))
        self.assertEqual(UPDATER.cost_per_1k(model), 0.018)
        self.assertIsNone(UPDATER.cost_per_1k({"pricing": {"prompt": "bad"}}))
        self.assertIsNone(UPDATER.cost_per_1k({"pricing": {"prompt": "0.1"}}))
        self.assertIsNone(UPDATER.cost_per_1k({"pricing": {"prompt": "NaN", "completion": "1"}}))

    def test_fetch_uses_optional_environment_key_without_logging_it(self):
        response = io.BytesIO(b'{"data": []}')
        with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            with mock.patch.object(UPDATER.urllib.request, "urlopen", return_value=response) as urlopen:
                self.assertEqual(UPDATER.fetch("https://example.invalid/models"), {"data": []})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertNotIn("test-key", request.full_url)

    def test_outputs_text_supports_current_and_legacy_schemas(self):
        self.assertTrue(UPDATER.outputs_text({"architecture": {"output_modalities": ["text"]}}))
        self.assertTrue(UPDATER.outputs_text({"architecture": {"modality": "text+image->text"}}))
        self.assertFalse(UPDATER.outputs_text({"architecture": {"output_modalities": ["image"]}}))
        self.assertFalse(UPDATER.outputs_text({"architecture": {"modality": "text->image"}}))
        self.assertTrue(UPDATER.outputs_text({}))  # unknown schema remains permissive

    def test_refresh_selects_newest_text_models_and_preserves_local_tier(self):
        def model(model_id, created, modality="text", prompt="0.000003", completion="0.000015"):
            return {
                "id": model_id,
                "created": created,
                "context_length": 128000,
                "architecture": {"output_modalities": [modality]},
                "pricing": {"prompt": prompt, "completion": completion},
            }

        models = [
            model("anthropic/claude-opus-6", 30),
            model("anthropic/claude-sonnet-6", 25),
            model("openai/gpt-5-mini", 50),
            model("google/gemini-8-pro", 40),
            model("openai/gpt-5-image", 99, modality="image"),
            model("google/gemini-8-flash", 49),
            model("openai/gpt-4o-mini", 10),
            model("anthropic/claude-haiku-4.5", 1),
        ]
        updated = UPDATER.refresh(IDX, models)
        # Discovery must not silently treat newest as best or auto-change routing.
        self.assertEqual(updated["aliases"], IDX["aliases"])
        self.assertEqual(updated["models"]["budget_fast"][0]["id"], "openai/gpt-5-mini")
        self.assertIn(IDX["aliases"]["budget_fast"],
                      [entry["id"] for entry in updated["models"]["budget_fast"]])
        self.assertEqual(updated["models"]["standard_coding"][0]["id"], "anthropic/claude-sonnet-6")
        self.assertEqual(updated["models"]["premium_reasoning"][0]["id"], "google/gemini-8-pro")
        self.assertEqual(updated["aliases"]["local_zero_token"], IDX["aliases"]["local_zero_token"])
        self.assertEqual(updated["models"]["budget_fast"][0]["prompt_per_1k_usd"], 0.003)
        self.assertEqual(updated["models"]["budget_fast"][0]["completion_per_1k_usd"], 0.015)
        self.assertEqual(updated["models"]["budget_fast"][0]["cost_per_1k_usd"], 0.018)
        promoted = UPDATER.refresh(IDX, models, promote_newest=True)
        self.assertEqual(promoted["aliases"]["budget_fast"], "openai/gpt-5-mini")
        self.assertEqual(promoted["aliases"]["standard_coding"], "anthropic/claude-sonnet-6")
        self.assertEqual(promoted["aliases"]["premium_reasoning"], "google/gemini-8-pro")

    def test_refresh_preserves_last_known_alias_and_catalog_when_no_match(self):
        index = json.loads(json.dumps(IDX))
        index["models"] = {"budget_fast": [{"id": index["aliases"]["budget_fast"],
                                               "prompt_per_1k_usd": 0.1,
                                               "completion_per_1k_usd": 0.2,
                                               "cost_per_1k_usd": 0.3}]}
        old_alias = index["aliases"]["budget_fast"]
        refreshed = UPDATER.refresh(index, [{"id": "some/unrelated-text-model",
                                              "architecture": {"output_modalities": ["text"]}}])
        self.assertEqual(refreshed["aliases"]["budget_fast"], old_alias)
        self.assertEqual(refreshed["models"]["budget_fast"][0]["id"], old_alias)

    def test_invalid_catalog_is_rejected(self):
        broken = json.loads(json.dumps(IDX))
        broken["tasks"][0]["tier"] = "missing-tier"
        self.assertTrue(any("unknown tier" in error for error in UPDATER.validate(broken)))
        broken["tasks"][0]["tier"] = []
        self.assertTrue(any("unknown tier" in error for error in UPDATER.validate(broken)))
        self.assertTrue(UPDATER.validate(None))

    def test_network_failure_leaves_index_bytes_untouched(self):
        original = INDEX_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            path.write_bytes(original)
            output = io.StringIO()
            with mock.patch.object(UPDATER, "fetch", side_effect=OSError("offline")):
                with contextlib.redirect_stderr(output):
                    result = UPDATER.main(["--index", str(path)])
            self.assertEqual(result, 1)
            self.assertEqual(path.read_bytes(), original)
            self.assertIn("kept as-is", output.getvalue())

    def test_dry_run_does_not_modify_the_index(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            original = INDEX_PATH.read_bytes()
            path.write_bytes(original)
            api_response = {"data": [{
                "id": "openai/gpt-5-mini",
                "created": 10,
                "architecture": {"output_modalities": ["text"]},
                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
            }]}
            output = io.StringIO()
            with mock.patch.object(UPDATER, "fetch", return_value=api_response):
                with contextlib.redirect_stdout(output):
                    result = UPDATER.main(["--dry-run", "--index", str(path)])
            self.assertEqual(result, 0)
            self.assertEqual(path.read_bytes(), original)
            self.assertIn("openai/gpt-5-mini", output.getvalue())

    def test_atomic_write_cleans_temporary_file_when_replace_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "index.json"
            with mock.patch.object(UPDATER.os, "replace", side_effect=OSError("blocked")):
                with self.assertRaises(OSError):
                    UPDATER.atomic_write(target, "contents")
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
