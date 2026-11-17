#!/usr/bin/env python3
"""Fail-closed constitutional preflight. Stdlib only; never executes an action."""
import argparse
import json
import pathlib
import sys

RULES = (
    "known_action", "known_repository", "no_protected_branch_write",
    "no_secret_access", "no_destructive_operation", "no_permission_escalation",
    "no_unreviewed_external_publish", "no_unverified_deployment",
    "no_unbounded_spend", "no_policy_modification", "tests_required",
    "human_approval_for_high_risk",
)
ALLOWED = {"read", "propose_patch", "run_tests", "open_pull_request"}
PROTECTED = {"main", "master", "production", "release"}
HIGH_RISK = {"deploy", "delete", "rotate_secret", "change_permissions", "merge"}
SENSITIVE = ("secret", "token", ".env", "credential", "private_key")

def evaluate(action, repositories):
    failures = []
    def deny(rule, reason):
        failures.append({"rule": rule, "reason": reason})
    kind = action.get("type")
    repo = action.get("repository")
    branch = action.get("branch", "")
    paths = action.get("paths", [])
    if kind not in ALLOWED:
        deny("known_action", "Action is not in the explicit allowlist")
    if not isinstance(repo, str) or repo not in repositories:
        deny("known_repository", "Repository is not in the approved inventory")
    if kind != "read" and branch in PROTECTED:
        deny("no_protected_branch_write", "Protected branch")
    if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
        deny("no_secret_access", "Invalid paths")
        paths = []
    if any(any(s in p.lower() for s in SENSITIVE) for p in paths):
        deny("no_secret_access", "Sensitive path")
    if kind in {"delete", "force_push"}:
        deny("no_destructive_operation", "Destructive operation")
    if kind == "change_permissions":
        deny("no_permission_escalation", "Permission change")
    if kind in {"publish", "post", "send_message"}:
        deny("no_unreviewed_external_publish", "External publication")
    if kind == "deploy" and not action.get("verified"):
        deny("no_unverified_deployment", "Unverified deployment")
    cost = action.get("estimated_cost_usd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not (0 <= cost <= 0):
        deny("no_unbounded_spend", "Missing or nonzero cost estimate")
    if any(p.startswith(("policy/", "constitution/")) for p in paths):
        deny("no_policy_modification", "Policy files cannot be changed by agents")
    if kind in {"propose_patch", "open_pull_request"} and action.get("tests_passed") is not True:
        deny("tests_required", "Passing tests required")
    if kind in HIGH_RISK and action.get("human_approved") is not True:
        deny("human_approval_for_high_risk", "Explicit human approval required")
    return {"allowed": not failures, "failures": failures, "rules_checked": list(RULES)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, help="JSON list of approved repository names")
    parser.add_argument("--action", required=True, help="JSON action file")
    args = parser.parse_args()
    try:
        inventory = json.loads(pathlib.Path(args.inventory).read_text())
        action = json.loads(pathlib.Path(args.action).read_text())
        if not isinstance(inventory, list) or not isinstance(action, dict):
            raise ValueError("Expected list inventory and object action")
        result = evaluate(action, inventory)
    except (OSError, ValueError, TypeError) as exc:
        result = {"allowed": False, "failures": [{"rule": "input_validation", "reason": str(exc)}]}
    print(json.dumps(result, indent=2))
    return 0 if result["allowed"] else 2

if __name__ == "__main__":
    sys.exit(main())
