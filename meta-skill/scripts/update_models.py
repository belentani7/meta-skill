#!/usr/bin/env python3
"""Refresh the model catalog in index.json from OpenRouter's public model list.

- Stdlib only; no API key is requested or stored.
- Keeps separate input/output rates for auditable cost estimates.
- Atomic writes; a failed request or invalid response never replaces the index.
- The local_zero_token tier is never auto-updated.

Usage:
  python3 meta-skill/scripts/update_models.py
  python3 meta-skill/scripts/update_models.py --dry-run
  python3 meta-skill/scripts/update_models.py --promote-newest  # explicit, unbenchmarked promotion
  python3 meta-skill/scripts/update_models.py --validate
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

INDEX = Path(__file__).resolve().parent.parent / "index.json"
OPENROUTER = "https://openrouter.ai/api/v1/models"
REQUIRED = ("settings", "aliases", "alias_patterns", "tasks")
LOCAL_TIER = "local_zero_token"


def fetch(url: str) -> Any:
    headers = {"User-Agent": "meta-skill/1.1", "Accept": "application/json"}
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def _non_negative_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def pricing_per_1k(model: dict[str, Any]) -> tuple[float, float] | None:
    """Return per-1k input/output rates; missing or invalid rates stay unknown."""
    pricing = model.get("pricing")
    if not isinstance(pricing, dict):
        return None
    prompt = _non_negative_number(pricing.get("prompt"))
    completion = _non_negative_number(pricing.get("completion"))
    if prompt is None or completion is None:
        return None
    return round(prompt * 1000, 9), round(completion * 1000, 9)


def cost_per_1k(model: dict[str, Any]) -> float | None:
    """Cost of 1k input plus 1k output tokens, or None when either rate is unknown."""
    rates = pricing_per_1k(model)
    if rates is None:
        return None
    return round(sum(rates), 6)


def outputs_text(model: dict[str, Any]) -> bool:
    """True for text-output models; tolerate older/incomplete catalog schemas."""
    architecture = model.get("architecture") or {}
    if not isinstance(architecture, dict):
        return True
    output_modalities = architecture.get("output_modalities")
    if isinstance(output_modalities, list):
        return any(isinstance(modality, str) and modality.casefold() == "text"
                   for modality in output_modalities)
    modality = architecture.get("modality") or "text->text"
    return "text" in str(modality).split("->")[-1].casefold()


def validate(index: Any) -> list[str]:
    """Offline structural/data-integrity check. Empty list means valid."""
    if not isinstance(index, dict):
        return ["index root must be an object"]
    errors: list[str] = []
    for key in REQUIRED:
        if key not in index:
            errors.append(f"missing key: {key}")

    settings = index.get("settings")
    if not isinstance(settings, dict):
        errors.append("settings must be an object")
        settings = {}
    aliases = index.get("aliases")
    if not isinstance(aliases, dict):
        errors.append("aliases must be an object")
        aliases = {}
    for tier, alias in aliases.items():
        if not isinstance(tier, str) or not tier.strip():
            errors.append("alias tier names must be non-empty strings")
        if not isinstance(alias, str) or not alias.strip():
            errors.append(f"alias {tier!r} must be a non-empty string")

    patterns_by_tier = index.get("alias_patterns")
    if not isinstance(patterns_by_tier, dict):
        errors.append("alias_patterns must be an object")
        patterns_by_tier = {}
    if LOCAL_TIER in patterns_by_tier:
        errors.append(f"{LOCAL_TIER} must never be auto-updated")
    for tier, patterns in patterns_by_tier.items():
        if tier not in aliases:
            errors.append(f"alias_patterns tier not in aliases: {tier}")
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"alias_patterns {tier}: expected a non-empty list")
            continue
        for pattern in patterns:
            if not isinstance(pattern, str):
                errors.append(f"alias_patterns {tier}: each pattern must be a string")
                continue
            try:
                re.compile(pattern, re.I)
            except re.error as exc:
                errors.append(f"bad regex {tier}:{pattern!r} ({exc})")

    tasks = index.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        errors.append("tasks must be a non-empty list")
        tasks = []
    seen: set[str] = set()
    for position, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            errors.append(f"task #{position} must be an object")
            continue
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip():
            errors.append(f"task #{position}: id must be a non-empty string")
            task_id = f"#{position}"
        if task_id in seen:
            errors.append(f"duplicate task id: {task_id}")
        seen.add(task_id)
        keywords = task.get("keywords")
        if not isinstance(keywords, list) or not keywords or any(
                not isinstance(word, str) or not word.strip() for word in keywords):
            errors.append(f"task {task_id}: keywords must be a non-empty list of strings")
        complexity = task.get("complexity")
        if isinstance(complexity, bool) or not isinstance(complexity, int) or not 1 <= complexity <= 5:
            errors.append(f"task {task_id}: complexity must be an integer from 1 to 5")
        primary = task.get("tier")
        if not isinstance(primary, str) or primary not in aliases:
            errors.append(f"task {task_id}: unknown tier {primary}")
        fallbacks = task.get("fallback", [])
        if not isinstance(fallbacks, list):
            errors.append(f"task {task_id}: fallback must be a list")
            fallbacks = []
        if primary in fallbacks:
            errors.append(f"task {task_id}: fallback cannot include its primary tier")
        for tier in fallbacks:
            if not isinstance(tier, str) or tier not in aliases:
                errors.append(f"task {task_id}: unknown tier {tier}")
        tools = task.get("tools", [])
        if not isinstance(tools, list) or any(not isinstance(tool, str) for tool in tools):
            errors.append(f"task {task_id}: tools must be a list of strings")
        if not isinstance(task.get("directive"), str) or not task["directive"].strip():
            errors.append(f"task {task_id}: directive must be a non-empty string")

    default_tier = settings.get("default_tier")
    if default_tier is not None and (
            not isinstance(default_tier, str) or default_tier not in aliases):
        errors.append(f"settings.default_tier references unknown tier: {default_tier}")
    for field in ("max_cost_per_task_usd", "chars_per_token", "confidence_temperature"):
        if field in settings:
            number = _non_negative_number(settings[field])
            if number is None or (field != "max_cost_per_task_usd" and number <= 0):
                errors.append(f"settings.{field} must be a valid non-negative number")
    for field in ("minimum_route_confidence", "minimum_route_margin"):
        if field in settings:
            number = _non_negative_number(settings[field])
            if number is None or number > 1:
                errors.append(f"settings.{field} must be between 0 and 1")
    for field in ("token_budget_per_task", "estimated_output_tokens"):
        if field in settings:
            number = settings[field]
            if isinstance(number, bool) or not isinstance(number, int) or number < 1:
                errors.append(f"settings.{field} must be a positive integer")

    catalog = index.get("models", {})
    if not isinstance(catalog, dict):
        errors.append("models must be an object")
    else:
        for tier, entries in catalog.items():
            if tier == "note":
                continue
            if not isinstance(entries, list):
                errors.append(f"models.{tier} must be a list")
                continue
            for entry in entries:
                if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                        or not entry["id"].strip()):
                    errors.append(f"models.{tier}: each entry must have a non-empty string id")
                    continue
                for rate_field in ("prompt_per_1k_usd", "completion_per_1k_usd", "cost_per_1k_usd"):
                    if rate_field in entry and entry[rate_field] is not None:
                        if _non_negative_number(entry[rate_field]) is None:
                            errors.append(f"models.{tier}/{entry['id']}: invalid {rate_field}")
    return errors


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(dir=str(path.parent), prefix=".index-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _created(model: dict[str, Any]) -> float:
    value = model.get("created")
    if isinstance(value, bool):
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) and number >= 0 else 0.0


def _catalog_record(model: dict[str, Any]) -> dict[str, Any]:
    rates = pricing_per_1k(model)
    record: dict[str, Any] = {
        "id": model["id"],
        "prompt_per_1k_usd": rates[0] if rates is not None else None,
        "completion_per_1k_usd": rates[1] if rates is not None else None,
        "cost_per_1k_usd": cost_per_1k(model),
        "context": model.get("context_length"),
        "created": model.get("created"),
    }
    return record


def refresh(index: dict[str, Any], data: list[Any], *,
            promote_newest: bool = False) -> dict[str, Any]:
    """Refresh candidates; only promote a model when explicitly requested.

    Creation date and regex matches are discovery metadata, not evidence of
    quality. The shipped alias is therefore kept pinned by default.
    """
    if not isinstance(data, list):
        raise ValueError("unexpected OpenRouter schema: 'data' is not a list")
    updated = json.loads(json.dumps(index))
    catalog = updated.get("models", {})
    if not isinstance(catalog, dict):
        catalog = {}
    catalog["note"] = "auto-generated by scripts/update_models.py (source: OpenRouter public API)"

    for tier, patterns in updated.get("alias_patterns", {}).items():
        compiled = [re.compile(pattern, re.I) for pattern in patterns]
        candidates = [model for model in data
                      if isinstance(model, dict)
                      and isinstance(model.get("id"), str)
                      and model["id"]
                      and outputs_text(model)
                      and any(pattern.search(model["id"]) for pattern in compiled)]
        candidates.sort(key=lambda model: (-_created(model), model["id"].casefold()))
        if not candidates:
            # Keep both the last known alias and its pricing rather than erasing it.
            continue
        chosen = candidates[0]
        previous_alias = updated["aliases"].get(tier)
        selected_candidates = candidates[:3]
        pinned = next((model for model in candidates if model["id"] == previous_alias), None)
        if pinned is not None and all(model["id"] != previous_alias for model in selected_candidates):
            selected_candidates.append(pinned)
        if promote_newest:
            updated["aliases"][tier] = chosen["id"]
        catalog[tier] = [_catalog_record(model) for model in selected_candidates]
    updated["models"] = catalog
    updated["updated"] = date.today().isoformat()
    errors = validate(updated)
    if errors:
        raise ValueError("refusing invalid refreshed index: " + "; ".join(errors))
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate", action="store_true", help="offline structural check")
    mode.add_argument("--dry-run", action="store_true", help="print updated JSON; write nothing")
    parser.add_argument("--promote-newest", action="store_true",
                        help="promote the newest regex match (not a quality benchmark)")
    parser.add_argument("--index", type=Path, default=INDEX, help="path to index.json")
    args = parser.parse_args(argv)

    try:
        index = json.loads(args.index.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[meta-skill] cannot read index.json ({exc})", file=sys.stderr)
        return 1

    if args.validate:
        errors = validate(index)
        for error in errors:
            print(f"[meta-skill] INVALID: {error}")
        task_count = len(index.get("tasks", [])) if isinstance(index, dict) else 0
        tier_count = len(index.get("aliases", {})) if isinstance(index, dict) else 0
        print(f"[meta-skill] validate: {'FAIL' if errors else 'OK'} "
              f"({task_count} tasks, {tier_count} tiers)")
        return 1 if errors else 0

    try:
        response = fetch(OPENROUTER)
        if not isinstance(response, dict) or not isinstance(response.get("data"), list):
            raise ValueError("unexpected OpenRouter schema: expected an object containing a data list")
        updated = refresh(index, response["data"], promote_newest=args.promote_newest)
    except Exception as exc:  # Preserve the last known catalog on every fetch/parse failure.
        print(f"[meta-skill] refresh failed ({exc}); index.json kept as-is", file=sys.stderr)
        return 1

    serialized = json.dumps(updated, indent=2, ensure_ascii=False) + "\n"
    if args.dry_run:
        print(serialized, end="")
        return 0
    try:
        atomic_write(args.index, serialized)
    except OSError as exc:
        print(f"[meta-skill] cannot write index.json ({exc})", file=sys.stderr)
        return 1
    print(f"[meta-skill] index.json updated {updated['updated']}:")
    for tier, alias in updated["aliases"].items():
        entries = updated.get("models", {}).get(tier, [])
        newest = entries[0].get("id") if entries and isinstance(entries[0], dict) else None
        if args.promote_newest and newest:
            print(f"  {tier}: promoted {alias}")
        elif newest and newest != alias:
            print(f"  {tier}: kept {alias}; newest candidate is {newest} (review before promotion)")
        else:
            print(f"  {tier}: kept {alias}")
    if not args.promote_newest:
        print("[meta-skill] aliases remain pinned; use --promote-newest only after reviewing quality, cost, and capability")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
