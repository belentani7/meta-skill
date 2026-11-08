#!/usr/bin/env python3
"""Fail-closed, dependency-free policy gate for proposed autonomous actions.

This is a CI policy check, not a sandbox or GitHub permissions boundary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath

ALLOWED_ACTIONS = {"observe", "diagnose", "propose_patch", "open_pr", "run_tests"}
PROTECTED = (
    "governance/", ".github/workflows/", ".github/CODEOWNERS",
    "secrets/", ".env", "infra/production/", "terraform/",
)


def assess(proposal: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(proposal, dict):
        return ["proposal must be an object"]
    action = proposal.get("action")
    if action not in ALLOWED_ACTIONS:
        errors.append("action is not allowlisted")
    if proposal.get("environment") not in {"sandbox", "staging", "none"}:
        errors.append("environment must be sandbox, staging or none")
    if proposal.get("requires_human_approval") is False:
        errors.append("explicit human approval must not be disabled")
    paths = proposal.get("paths", [])
    if not isinstance(paths, list) or any(not isinstance(p, str) for p in paths):
        return errors + ["paths must be an array of strings"]
    for path in paths:
        norm = path.replace("\\", "/")
        parts = PurePosixPath(norm).parts
        if not norm or norm.startswith("/") or ".." in parts or norm.startswith("~"):
            errors.append(f"unsafe path: {path}")
        elif any(norm == prefix.rstrip("/") or norm.startswith(prefix) for prefix in PROTECTED):
            errors.append(f"protected path: {path}")
    if action in {"propose_patch", "open_pr"} and not paths:
        errors.append("patch proposals require explicit paths")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposal", help="JSON file containing one action proposal")
    args = parser.parse_args()
    try:
        with open(args.proposal, encoding="utf-8") as stream:
            proposal = json.load(stream)
        errors = assess(proposal)
    except (OSError, ValueError) as exc:
        errors = [f"invalid proposal: {exc}"]
    print(json.dumps({"allowed": not errors, "reasons": errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
