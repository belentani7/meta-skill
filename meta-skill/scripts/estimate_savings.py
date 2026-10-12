#!/usr/bin/env python3
"""Compare task-tier spend with a fixed-model baseline using aggregate data.

This is an offline calculator, not a billing report or a quality benchmark. It
requires observed request counts, average token counts, and exact model prices.
No prompt text is needed or saved.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from route import INDEX, estimate_model_cost, model_context_limit, model_record_for_tier

DEFAULT_BASELINE = "premium_reasoning"
NO_MODEL_TIERS = {"local_zero_token"}


def _positive_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _token_average(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite, non-negative number")
    try:
        tokens = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a finite, non-negative number") from None
    if not math.isfinite(tokens) or tokens < 0:
        raise ValueError(f"{field} must be a finite, non-negative number")
    return tokens


def _cost_for(index: dict[str, Any], tier: str,
              input_tokens: float, output_tokens: float,
              max_input_tokens: float | None,
              max_output_tokens: float | None) -> dict[str, Any]:
    model = index.get("aliases", {}).get(tier)
    if tier in NO_MODEL_TIERS or (
            isinstance(model, str) and "without a model call" in model.casefold()):
        return {"model": model, "cost": 0.0, "status": "no_model_call",
                "context_status": "not_applicable"}

    record = model_record_for_tier(index, tier)
    if record is None:
        return {"model": model, "cost": None, "status": "price_unknown",
                "context_status": "context_unknown"}

    context_tokens = model_context_limit(record) or 0
    average_total = input_tokens + output_tokens
    observed_max_total = None
    if max_input_tokens is not None and max_output_tokens is not None:
        observed_max_total = max_input_tokens + max_output_tokens
    if context_tokens > 0 and average_total > context_tokens:
        return {"model": model, "cost": None, "status": "context_too_small_for_average",
                "context_status": "average_exceeds_context"}
    if (context_tokens > 0 and observed_max_total is not None
            and observed_max_total > context_tokens):
        return {"model": model, "cost": None, "status": "context_too_small_for_observed_max",
                "context_status": "observed_max_exceeds_context"}

    if context_tokens <= 0:
        context_status = "context_unknown"
    elif observed_max_total is None:
        context_status = "average_fits_tail_unknown"
    else:
        context_status = "observed_max_fits"
    cost = estimate_model_cost(record, input_tokens, output_tokens)
    if cost is None:
        return {"model": model, "cost": None, "status": "price_unknown",
                "context_status": context_status}
    if context_tokens <= 0:
        return {"model": model, "cost": cost, "status": "priced_context_unknown",
                "context_status": context_status}
    if observed_max_total is None:
        return {"model": model, "cost": cost, "status": "priced_average_context_fit",
                "context_status": context_status}
    return {"model": model, "cost": cost, "status": "priced_observed_max_context_fit",
            "context_status": context_status}


def _context_problem(result: dict[str, Any]) -> bool:
    return result.get("status") in {
        "context_too_small_for_average", "context_too_small_for_observed_max"
    }


def _select_task_route(index: dict[str, Any], task: dict[str, Any],
                       input_tokens: float, output_tokens: float,
                       max_input: float | None, max_output: float | None,
                       max_cost: float | None) -> tuple[str | None, dict[str, Any], str, str | None]:
    primary_tier = task.get("tier")
    primary = _cost_for(index, primary_tier, input_tokens, output_tokens, max_input, max_output)
    context_limited = _context_problem(primary)
    over_budget = primary["cost"] is not None and max_cost is not None and primary["cost"] > max_cost
    if not context_limited and not over_budget:
        return primary_tier, primary, primary["status"], None

    alternatives = []
    fallback_tiers = task.get("fallback", [])
    if not isinstance(fallback_tiers, list):
        fallback_tiers = []
    seen_tiers = set()
    for position, tier in enumerate(fallback_tiers):
        if not isinstance(tier, str) or tier in seen_tiers:
            continue
        seen_tiers.add(tier)
        if tier not in index.get("aliases", {}):
            continue
        candidate = _cost_for(index, tier, input_tokens, output_tokens, max_input, max_output)
        if _context_problem(candidate) or candidate["context_status"] == "context_unknown":
            continue
        candidate_cost = candidate["cost"]
        if candidate_cost is None and (max_cost is not None or not context_limited):
            continue
        if candidate_cost is not None and max_cost is not None and candidate_cost > max_cost:
            continue
        alternatives.append((candidate_cost, position, tier, candidate))
    if alternatives:
        key = (lambda item: item[1]) if context_limited else (lambda item: (item[0], item[1]))
        _, _, selected_tier, selected = min(alternatives, key=key)
        status = "context_fallback_selected" if context_limited else "fallback_selected"
        return selected_tier, selected, status, primary_tier

    reason = "blocked_by_context_limit" if context_limited else "blocked_by_budget"
    blocked = {"model": None, "cost": None, "status": reason,
               "context_status": primary.get("context_status", "not_checked")}
    return None, blocked, reason, primary_tier


def estimate_savings(workload: Any, index: dict[str, Any],
                     baseline_tier: str = DEFAULT_BASELINE,
                     budget_usd: float | None = None) -> dict[str, Any]:
    """Compare configured task-tier routing with one fixed baseline tier."""
    if not isinstance(index, dict):
        raise ValueError("index must be an object")
    aliases = index.get("aliases")
    if (not isinstance(aliases, dict) or not isinstance(baseline_tier, str)
            or baseline_tier not in aliases):
        raise ValueError(f"unknown baseline tier: {baseline_tier}")
    tasks = index.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("index tasks must be a list")
    if not isinstance(index.get("models", {}), dict):
        raise ValueError("index models must be an object")
    if budget_usd is None:
        settings = index.get("settings")
        budget_usd = settings.get("max_cost_per_task_usd") if isinstance(settings, dict) else None
    if budget_usd is not None:
        if isinstance(budget_usd, bool):
            raise ValueError("max cost per task must be a finite, non-negative number")
        try:
            budget_usd = float(budget_usd)
        except (TypeError, ValueError):
            raise ValueError("max cost per task must be a finite, non-negative number") from None
        if not math.isfinite(budget_usd) or budget_usd < 0:
            raise ValueError("max cost per task must be a finite, non-negative number")
    task_by_id = {task.get("id"): task for task in tasks if isinstance(task, dict)
                  and isinstance(task.get("id"), str)}
    observations = workload.get("observations") if isinstance(workload, dict) else workload
    if not isinstance(observations, list) or not observations:
        raise ValueError("workload must contain a non-empty observations list")

    rows: list[dict[str, Any]] = []
    routed_total = 0.0
    baseline_total = 0.0
    routed_complete = True
    baseline_complete = True
    context_complete = True
    total_requests = 0

    for position, observation in enumerate(observations, start=1):
        if not isinstance(observation, dict):
            raise ValueError(f"observation #{position} must be an object")
        task_id = observation.get("task_id")
        if not isinstance(task_id, str) or task_id not in task_by_id:
            raise ValueError(f"observation #{position} has unknown task_id {task_id!r}")
        count = _positive_integer(observation.get("requests"), f"observation #{position}.requests")
        input_tokens = _token_average(
            observation.get("avg_input_tokens"), f"observation #{position}.avg_input_tokens")
        output_tokens = _token_average(
            observation.get("avg_output_tokens"), f"observation #{position}.avg_output_tokens")
        max_input = (None if observation.get("max_input_tokens") is None else
                     _token_average(observation["max_input_tokens"],
                                    f"observation #{position}.max_input_tokens"))
        max_output = (None if observation.get("max_output_tokens") is None else
                      _token_average(observation["max_output_tokens"],
                                     f"observation #{position}.max_output_tokens"))
        if (max_input is None) != (max_output is None):
            raise ValueError(f"observation #{position}: provide both max token fields or neither")
        if (max_input is not None and max_output is not None
                and (max_input < input_tokens or max_output < output_tokens)):
            raise ValueError(f"observation #{position}: max token counts cannot be below averages")

        task = task_by_id[task_id]
        configured_tier = task.get("tier")
        if not isinstance(configured_tier, str) or configured_tier not in aliases:
            raise ValueError(f"task {task_id} references unknown tier {configured_tier!r}")
        route_tier, routed, routed_status, fallback_from = _select_task_route(
            index, task, input_tokens, output_tokens, max_input, max_output, budget_usd)
        baseline = _cost_for(index, baseline_tier, input_tokens, output_tokens, max_input, max_output)
        route_cost = routed["cost"]
        baseline_cost = baseline["cost"]
        if route_cost is None:
            routed_complete = False
        else:
            routed_total += route_cost * count
        if baseline_cost is None:
            baseline_complete = False
        else:
            baseline_total += baseline_cost * count
        if (routed["context_status"] not in {"observed_max_fits", "not_applicable"}
                or baseline["context_status"] not in {"observed_max_fits", "not_applicable"}):
            context_complete = False

        rows.append({
            "task_id": task_id,
            "requests": count,
            "average_input_tokens": round(input_tokens, 3),
            "average_output_tokens": round(output_tokens, 3),
            "observed_max_input_tokens": max_input,
            "observed_max_output_tokens": max_output,
            "configured_tier": configured_tier,
            "routed_tier": route_tier,
            "routed_model": routed["model"],
            "routed_status": routed_status,
            "fallback_from_tier": fallback_from,
            "routed_context_status": routed["context_status"],
            "routed_cost_usd": round(route_cost * count, 8) if route_cost is not None else None,
            "baseline_tier": baseline_tier,
            "baseline_model": baseline["model"],
            "baseline_status": baseline["status"],
            "baseline_context_status": baseline["context_status"],
            "baseline_cost_usd": round(baseline_cost * count, 8) if baseline_cost is not None else None,
            "estimated_savings_usd": round((baseline_cost - route_cost) * count, 8)
            if route_cost is not None and baseline_cost is not None else None,
        })
        total_requests += count

    routed_cost = round(routed_total, 8) if routed_complete else None
    baseline_cost = round(baseline_total, 8) if baseline_complete else None
    savings = baseline_cost - routed_cost if routed_cost is not None and baseline_cost is not None else None
    savings_percent = (
        round(savings / baseline_cost * 100, 4)
        if savings is not None and baseline_cost > 0 else None
    )
    return {
        "baseline_tier": baseline_tier,
        "max_cost_per_request_usd": budget_usd,
        "request_count": total_requests,
        "routed_cost_usd": routed_cost,
        "baseline_cost_usd": baseline_cost,
        "estimated_savings_usd": round(savings, 8) if savings is not None else None,
        "estimated_savings_percent": savings_percent,
        "routed_pricing_complete": routed_complete,
        "baseline_pricing_complete": baseline_complete,
        "observed_context_complete": context_complete,
        "context_assumption": "maximum token counts are needed to check observed context fit; future outliers remain possible",
        "quality_status": "not_measured; compare task quality before adopting a cheaper route",
        "interpretation": "modeled from supplied workload averages and catalog rates; not observed billing or a production savings claim",
        "observations": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", type=Path, required=True,
                        help="JSON with observations: task_id, requests, avg_input_tokens, avg_output_tokens")
    parser.add_argument("--index", type=Path, default=INDEX, help="path to index.json")
    parser.add_argument("--baseline-tier", default=DEFAULT_BASELINE,
                        help="fixed tier for cost comparison (default: premium_reasoning)")
    parser.add_argument("--max-cost", type=float, default=None,
                        help="override the index's maximum cost per request in USD")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        index = json.loads(args.index.read_text(encoding="utf-8"))
        workload = json.loads(args.workload.read_text(encoding="utf-8"))
        report = estimate_savings(workload, index, args.baseline_tier, args.max_cost)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"[meta-skill] savings estimate error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print("Estimated cost comparison — not billing or quality evidence")
    print(f"Requests: {report['request_count']}; baseline tier: {report['baseline_tier']}; "
          f"max request cost: {report['max_cost_per_request_usd']} USD")
    routed = report["routed_cost_usd"]
    baseline = report["baseline_cost_usd"]
    print(f"Task-tier policy: {routed if routed is not None else 'unknown'} USD")
    print(f"Fixed baseline: {baseline if baseline is not None else 'unknown'} USD")
    if report["estimated_savings_usd"] is None:
        print("Estimated savings: unknown (missing prices, blocked route, or context limit)")
    else:
        percent = report["estimated_savings_percent"]
        percent_text = f"{percent:.2f}%" if percent is not None else "n/a"
        print(f"Estimated savings: ${report['estimated_savings_usd']:.8f} "
              f"({percent_text})")
    print(f"Observed context complete: {report['observed_context_complete']}")
    print(report["quality_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
