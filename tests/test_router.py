"""Offline router tests: language matching, abstention, budgets, and privacy."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "meta-skill" / "scripts"
INDEX = json.loads((ROOT / "meta-skill" / "index.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(SCRIPTS))
from route import route_prompt  # noqa: E402
from estimate_savings import estimate_savings  # noqa: E402


def load_evaluator():
    path = SCRIPTS / "evaluate_router.py"
    spec = importlib.util.spec_from_file_location("meta_skill_evaluate_router", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EVALUATOR = load_evaluator()


class TestRouting(unittest.TestCase):
    def test_smoke_set_routes_all_clear_examples_and_abstains_on_unknowns(self):
        dataset = json.loads((ROOT / "meta-skill" / "evaluations" / "smoke.json").read_text(encoding="utf-8"))
        report = EVALUATOR.evaluate_cases(dataset["cases"], INDEX)
        self.assertEqual(report["case_count"], 39)
        self.assertEqual(report["accuracy_including_abstentions"], 1.0)
        self.assertEqual(report["abstentions"], 3)
        self.assertIn("not a production", report["interpretation"])

    def test_spanish_accents_case_and_punctuation(self):
        result = route_prompt("AUDITORÍA de SEGURIDAD: busca vulnerabilidades y XSS.", INDEX)
        self.assertEqual(result["task_id"], "security_audit")
        self.assertGreaterEqual(result["confidence"], INDEX["settings"]["minimum_route_confidence"])

    def test_ambiguous_keyword_abstains_instead_of_guessing(self):
        result = route_prompt("Set up a shared pipeline.", INDEX)
        self.assertEqual(result["decision"], "needs_review")
        self.assertIsNone(result["task_id"])
        self.assertIn(result["candidate_task_id"], {"devops_iac", "data_etl"})
        self.assertEqual(result["tier"], INDEX["settings"]["default_tier"])

    def test_unknown_prompt_uses_safe_default_not_quick_fix(self):
        result = route_prompt("Can you make this better for our team?", INDEX)
        self.assertEqual(result["decision"], "needs_review")
        self.assertEqual(result["reason"], "no_keyword_evidence")
        self.assertIsNone(result["task_id"])
        self.assertEqual(result["tier"], "standard_coding")

    def test_a_bug_is_not_misclassified_as_a_zero_token_typo(self):
        result = route_prompt("Fix this bug in the payment service.", INDEX)
        self.assertNotEqual(result["task_id"], "quick_fix")
        self.assertNotEqual(result["tier"], "local_zero_token")
        self.assertIn("not a calibrated probability", result["confidence_semantics"])

    def test_word_boundaries_avoid_api_substring_false_positive(self):
        result = route_prompt("The rapid plan is available.", INDEX)
        self.assertIsNone(result["task_id"])
        self.assertNotEqual(result["candidate_task_id"], "backend_api")

    def test_prompt_is_not_echoed_or_saved_in_result(self):
        secret_like_text = "Do not reveal my private prompt abc123; audit XSS."
        result = route_prompt(secret_like_text, INDEX)
        self.assertNotIn(secret_like_text, json.dumps(result))
        self.assertIn("does not transmit or persist", result["privacy"])
        self.assertIn("prefer stdin", result["privacy"])

    def test_claude_code_aliases_are_resolved_without_claiming_openrouter_cost(self):
        result = route_prompt("Build an accessible React component.", INDEX, runtime="claude_code")
        self.assertEqual(result["model"], "sonnet")
        self.assertIsNone(result["budget"]["estimated_cost_usd"])
        self.assertEqual(result["budget"]["status"], "price_unknown")
        self.assertEqual(result["decision"], "budget_unknown")
        self.assertTrue(result["requires_human_review"])

    def test_local_typo_path_recommends_no_model_call(self):
        result = route_prompt("Fix this typo in the configuration.", INDEX)
        self.assertEqual(result["tier"], "local_zero_token")
        self.assertIn("without a model call", result["model"])
        self.assertEqual(result["budget"]["status"], "no_model_call")
        self.assertEqual(result["budget"]["estimated_cost_usd"], 0.0)
        self.assertEqual(result["budget"]["estimated_total_tokens"], 0)

    def test_known_prices_can_trigger_a_verified_cheaper_fallback(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.1,
                "completion_per_1k_usd": 1.0,
                "context": 50000,
            }],
            "standard_coding": [{
                "id": index["aliases"]["standard_coding"],
                "prompt_per_1k_usd": 0.01,
                "completion_per_1k_usd": 0.02,
                "context": 50000,
            }],
        }
        result = route_prompt("Run a security audit for XSS and a CVE.", index)
        self.assertEqual(result["task_id"], "security_audit")
        self.assertEqual(result["tier"], "standard_coding")
        self.assertEqual(result["budget"]["status"], "fallback_selected")
        self.assertEqual(result["budget"]["fallback_from_tier"], "premium_reasoning")
        self.assertLessEqual(result["budget"]["estimated_cost_usd"], 0.5)

    def test_budget_guard_blocks_when_no_fallback_is_verified_affordable(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.1,
                "completion_per_1k_usd": 1.0,
                "context": 50000,
            }]
        }
        result = route_prompt("Run a security audit for XSS and a CVE.", index)
        self.assertEqual(result["decision"], "blocked_by_budget")
        self.assertIsNone(result["tier"])
        self.assertIsNone(result["model"])

    def test_context_limit_uses_a_fitting_and_affordable_fallback(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.1,
                "completion_per_1k_usd": 0.2,
                "context": 64,
            }],
            "standard_coding": [{
                "id": index["aliases"]["standard_coding"],
                "prompt_per_1k_usd": 0.01,
                "completion_per_1k_usd": 0.02,
                "context": 50000,
            }],
        }
        result = route_prompt("Run a security audit for XSS and a CVE.", index)
        self.assertEqual(result["tier"], "standard_coding")
        self.assertEqual(result["budget"]["status"], "context_fallback_selected")

    def test_token_budget_blocks_oversized_model_requests(self):
        index = copy.deepcopy(INDEX)
        index["settings"]["token_budget_per_task"] = 20
        index["settings"]["estimated_output_tokens"] = 10
        result = route_prompt("x" * 100, index)
        self.assertEqual(result["decision"], "blocked_by_token_budget")
        self.assertIsNone(result["model"])
        self.assertFalse(result["budget"]["within_token_limit"])

    def test_empty_prompt_and_unknown_runtime_fail_clearly(self):
        with self.assertRaises(ValueError):
            route_prompt("  ", INDEX)
        with self.assertRaises(ValueError):
            route_prompt("please test", INDEX, runtime="imaginary")

    def test_savings_estimate_uses_task_mix_and_exact_token_rates(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {}
        for tier, prompt_rate, completion_rate in (
                ("premium_reasoning", 0.01, 0.02),
                ("standard_coding", 0.005, 0.01),
                ("budget_fast", 0.002, 0.004)):
            index["models"][tier] = [{
                "id": index["aliases"][tier],
                "prompt_per_1k_usd": prompt_rate,
                "completion_per_1k_usd": completion_rate,
                "context": 50000,
            }]
        workload = {"observations": [
            {"task_id": "testing", "requests": 100, "avg_input_tokens": 1000,
             "avg_output_tokens": 1000, "max_input_tokens": 1500,
             "max_output_tokens": 1500},
            {"task_id": "backend_api", "requests": 50, "avg_input_tokens": 1000,
             "avg_output_tokens": 1000, "max_input_tokens": 1500,
             "max_output_tokens": 1500},
        ]}
        report = estimate_savings(workload, index)
        self.assertEqual(report["routed_cost_usd"], 1.35)
        self.assertEqual(report["baseline_cost_usd"], 4.5)
        self.assertEqual(report["estimated_savings_usd"], 3.15)
        self.assertEqual(report["estimated_savings_percent"], 70.0)
        self.assertTrue(report["observed_context_complete"])
        self.assertIn("not_measured", report["quality_status"])

    def test_savings_estimate_does_not_treat_missing_prices_as_free(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.01,
                "completion_per_1k_usd": 0.02,
                "context": 50000,
            }]
        }
        report = estimate_savings({"observations": [{
            "task_id": "testing", "requests": 10,
            "avg_input_tokens": 100, "avg_output_tokens": 100,
        }]}, index)
        self.assertIsNone(report["routed_cost_usd"])
        self.assertEqual(report["baseline_cost_usd"], 0.03)
        self.assertIsNone(report["estimated_savings_usd"])
        self.assertFalse(report["routed_pricing_complete"])

    def test_savings_estimate_models_budget_fallback_and_block(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.1,
                "completion_per_1k_usd": 0.2,
                "context": 50000,
            }],
            "standard_coding": [{
                "id": index["aliases"]["standard_coding"],
                "prompt_per_1k_usd": 0.05,
                "completion_per_1k_usd": 0.1,
                "context": 50000,
            }],
            "budget_fast": [{
                "id": index["aliases"]["budget_fast"],
                "prompt_per_1k_usd": 0.3,
                "completion_per_1k_usd": 0.4,
                "context": 50000,
            }],
        }
        workload = {"observations": [{
            "task_id": "testing", "requests": 10,
            "avg_input_tokens": 1000, "avg_output_tokens": 1000,
            "max_input_tokens": 1200, "max_output_tokens": 1200,
        }]}
        report = estimate_savings(workload, index)
        row = report["observations"][0]
        self.assertEqual(row["configured_tier"], "budget_fast")
        self.assertEqual(row["routed_tier"], "standard_coding")
        self.assertEqual(row["routed_status"], "fallback_selected")
        self.assertEqual(row["fallback_from_tier"], "budget_fast")
        self.assertEqual(report["routed_cost_usd"], 1.5)

        blocked = estimate_savings(workload, index, budget_usd=0.01)
        self.assertIsNone(blocked["routed_cost_usd"])
        self.assertEqual(blocked["observations"][0]["routed_status"], "blocked_by_budget")
        self.assertIsNone(blocked["estimated_savings_usd"])

    def test_savings_estimate_uses_fallback_when_average_exceeds_context(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.1,
                "completion_per_1k_usd": 0.2,
                "context": 50000,
            }],
            "standard_coding": [{
                "id": index["aliases"]["standard_coding"],
                "prompt_per_1k_usd": 0.05,
                "completion_per_1k_usd": 0.1,
                "context": 50000,
            }],
            "budget_fast": [{
                "id": index["aliases"]["budget_fast"],
                "context": 1000,
            }],
        }
        report = estimate_savings({"observations": [{
            "task_id": "testing", "requests": 1,
            "avg_input_tokens": 900, "avg_output_tokens": 200,
            "max_input_tokens": 1200, "max_output_tokens": 400,
        }]}, index)
        row = report["observations"][0]
        self.assertEqual(row["routed_tier"], "standard_coding")
        self.assertEqual(row["routed_status"], "context_fallback_selected")
        self.assertEqual(row["routed_context_status"], "observed_max_fits")

    def test_savings_estimate_marks_average_only_context_as_unverified(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "budget_fast": [{
                "id": index["aliases"]["budget_fast"],
                "prompt_per_1k_usd": 0.002,
                "completion_per_1k_usd": 0.004,
                "context": 50000,
            }],
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.01,
                "completion_per_1k_usd": 0.02,
                "context": 50000,
            }],
        }
        report = estimate_savings({"observations": [{
            "task_id": "testing", "requests": 10,
            "avg_input_tokens": 100, "avg_output_tokens": 100,
        }]}, index)
        self.assertIsNotNone(report["estimated_savings_usd"])
        self.assertFalse(report["observed_context_complete"])
        self.assertEqual(report["observations"][0]["routed_context_status"],
                         "average_fits_tail_unknown")

    def test_savings_cli_uses_an_external_priced_index(self):
        index = copy.deepcopy(INDEX)
        index["models"] = {
            "premium_reasoning": [{
                "id": index["aliases"]["premium_reasoning"],
                "prompt_per_1k_usd": 0.01,
                "completion_per_1k_usd": 0.02,
                "context": 50000,
            }],
            "budget_fast": [{
                "id": index["aliases"]["budget_fast"],
                "prompt_per_1k_usd": 0.002,
                "completion_per_1k_usd": 0.004,
                "context": 50000,
            }],
        }
        workload = {"observations": [{
            "task_id": "testing", "requests": 10,
            "avg_input_tokens": 1000, "avg_output_tokens": 500,
            "max_input_tokens": 1200, "max_output_tokens": 700,
        }]}
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "priced-index.json"
            workload_path = Path(temp_dir) / "workload.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            workload_path.write_text(json.dumps(workload), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "estimate_savings.py"),
                 "--index", str(index_path), "--workload", str(workload_path), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["routed_cost_usd"], 0.04)
        self.assertEqual(report["baseline_cost_usd"], 0.2)
        self.assertEqual(report["estimated_savings_usd"], 0.16)
        self.assertTrue(report["observed_context_complete"])

    def test_savings_cli_reports_unknown_prices_not_zero_cost(self):
        workload = {"observations": [{
            "task_id": "testing", "requests": 1,
            "avg_input_tokens": 50, "avg_output_tokens": 20,
        }]}
        with tempfile.TemporaryDirectory() as temp_dir:
            workload_path = Path(temp_dir) / "workload.json"
            workload_path.write_text(json.dumps(workload), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "estimate_savings.py"),
                 "--workload", str(workload_path), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertIsNone(report["routed_cost_usd"])
        self.assertIsNone(report["baseline_cost_usd"])
        self.assertIsNone(report["estimated_savings_usd"])
        self.assertIn("not observed billing", report["interpretation"])

    def test_cli_reads_stdin_and_emits_json_without_prompt(self):
        prompt = "Build an accessible React component."
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "route.py"), "--json"],
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["task_id"], "frontend_ui")
        self.assertNotIn(prompt, completed.stdout)


if __name__ == "__main__":
    unittest.main()
