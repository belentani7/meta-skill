"""CLI contract tests for the stdlib-only, streaming JSONL agent router."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTER = ROOT / "meta-skill" / "scripts" / "route.py"


def route_batch(records):
    return subprocess.run(
        [sys.executable, str(ROUTER), "--batch-jsonl"],
        input="\n".join(records) + "\n",
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
        timeout=30,
    )


class BatchRoutingTests(unittest.TestCase):
    def test_routes_multiple_requests_in_input_order(self):
        run = route_batch([
            json.dumps({"prompt": "Build a responsive React component."}),
            json.dumps({"prompt": "Fix this typo in the configuration."}),
        ])
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([row["line"] for row in rows], [1, 2])
        self.assertEqual(rows[0]["result"]["task_id"], "frontend_ui")
        self.assertEqual(rows[1]["result"]["tier"], "local_zero_token")

    def test_invalid_request_does_not_stop_later_routes(self):
        run = route_batch([
            "not-json",
            json.dumps({"prompt": "Fix this typo in the configuration."}),
            json.dumps({"prompt": ""}),
        ])
        self.assertEqual(run.returncode, 1)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertIn("error", rows[0])
        self.assertEqual(rows[1]["result"]["tier"], "local_zero_token")
        self.assertIn("error", rows[2])

    def test_does_not_echo_private_prompts_in_results_or_errors(self):
        secret = "my confidential phrase xyz-123"
        run = route_batch([
            json.dumps({"prompt": "Audit XSS for " + secret}),
            json.dumps({"prompt": secret, "unexpected": "field"}),
        ])
        self.assertNotIn(secret, run.stdout + run.stderr)

    def test_rejects_boolean_budget_instead_of_treating_it_as_one_dollar(self):
        run = route_batch([json.dumps({"prompt": "Build CSS", "budget_usd": True})])
        self.assertEqual(run.returncode, 1)
        self.assertIn("budget_usd", run.stdout)

    def test_blank_lines_do_not_create_phantom_tasks(self):
        run = route_batch(["", json.dumps({"prompt": "Fix this typo in the configuration."}), ""])
        self.assertEqual(run.returncode, 0)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["line"], 2)


if __name__ == "__main__":
    unittest.main()
