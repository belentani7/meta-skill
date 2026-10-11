#!/usr/bin/env python3
"""Offline, explainable Meta-Skill router (stdlib only).

This recommends a task/tier; it does not call a model, send prompts anywhere,
or claim that its keyword-derived confidence is a calibrated probability.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

INDEX = Path(__file__).resolve().parent.parent / "index.json"
LOCAL_TIER = "local_zero_token"


def tokenize(text: str) -> tuple[str, ...]:
    """Lowercase and remove accents/punctuation so ES/PT/EN match consistently."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return tuple(re.findall(r"[a-z0-9]+", plain))


def _term_key(term: str) -> tuple[str, ...]:
    return tokenize(term)


def _contains_phrase(tokens: tuple[str, ...], phrase: tuple[str, ...]) -> bool:
    if not phrase or len(phrase) > len(tokens):
        return False
    width = len(phrase)
    return any(tokens[pos:pos + width] == phrase
               for pos in range(len(tokens) - width + 1))


def _keyword_weights(tasks: list[dict[str, Any]]) -> dict[tuple[str, ...], float]:
    """Compute IDF-style weights; terms shared by tasks carry less evidence."""
    task_terms: list[set[tuple[str, ...]]] = []
    for task in tasks:
        task_terms.append({key for word in task.get("keywords", [])
                           if isinstance(word, str) and (key := _term_key(word))})

    weights: dict[tuple[str, ...], float] = {}
    for terms in task_terms:
        for key in terms:
            document_frequency = sum(key in other for other in task_terms)
            weights[key] = 1.0 + math.log((len(tasks) + 1) / (document_frequency + 1))
    return weights


def _softmax(scores: list[float], temperature: float) -> list[float]:
    scaled = [score / temperature for score in scores]
    peak = max(scaled, default=0.0)
    exps = [math.exp(value - peak) for value in scaled]
    denominator = sum(exps)
    return [value / denominator for value in exps] if denominator else []


def _model_for_tier(index: dict[str, Any], tier: str, runtime: str) -> str | None:
    aliases_key = "claude_code_aliases" if runtime == "claude_code" else "aliases"
    aliases = index.get(aliases_key)
    if not isinstance(aliases, dict):
        aliases = {}
    model = aliases.get(tier)
    if model is None and runtime == "claude_code":
        model = index.get("aliases", {}).get(tier)
    return str(model) if model is not None else None


def model_record_for_tier(index: dict[str, Any], tier: str) -> dict[str, Any] | None:
    """Find pricing/limits for the canonical catalog alias, if it is known."""
    model_id = index.get("aliases", {}).get(tier)
    models = index.get("models", {}).get(tier, [])
    if not isinstance(models, list):
        return None
    for model in models:
        if isinstance(model, dict) and model.get("id") == model_id:
            return model
    return None


def _rate(record: dict[str, Any] | None, key: str) -> float | None:
    if not record or key not in record:
        return None
    value = record[key]
    if isinstance(value, bool):
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    return rate if math.isfinite(rate) and rate >= 0 else None


def estimate_model_cost(record: dict[str, Any] | None,
                        input_tokens: float,
                        output_tokens: float) -> float | None:
    """Estimate cost only when both per-1k-token rates are explicitly known."""
    input_rate = _rate(record, "prompt_per_1k_usd")
    output_rate = _rate(record, "completion_per_1k_usd")
    if input_rate is None or output_rate is None:
        return None
    return input_rate * input_tokens / 1000 + output_rate * output_tokens / 1000


def model_context_fits(record: dict[str, Any] | None, total_tokens: int) -> bool:
    if not record or record.get("context") is None:
        return True
    try:
        context = int(record["context"])
    except (TypeError, ValueError):
        return True
    return context <= 0 or total_tokens <= context


def _is_no_model_call(tier: str, model: str | None) -> bool:
    return tier == LOCAL_TIER or (model is not None and "without a model call" in model.casefold())


def _cost_for_tier(index: dict[str, Any], tier: str,
                    input_tokens: int, output_tokens: int,
                    total_tokens: int, runtime_model: str | None,
                    runtime: str) -> tuple[float | None, bool]:
    if _is_no_model_call(tier, runtime_model):
        return 0.0, True
    # A vendor/model alias is not proof that its native CLI uses OpenRouter rates.
    if runtime != "generic" or runtime_model != index.get("aliases", {}).get(tier):
        return None, True
    record = model_record_for_tier(index, tier)
    if not model_context_fits(record, total_tokens):
        return None, False
    return estimate_model_cost(record, input_tokens, output_tokens), True


def route_prompt(prompt: str, index: dict[str, Any], *,
                 runtime: str = "generic", budget_usd: float | None = None) -> dict[str, Any]:
    """Classify a prompt and return an auditable, offline routing recommendation."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must contain at least one non-whitespace character")
    if runtime not in {"generic", "claude_code"}:
        raise ValueError("runtime must be 'generic' or 'claude_code'")
    if not isinstance(index, dict):
        raise ValueError("index must be a JSON object")

    tasks = index.get("tasks")
    if not isinstance(tasks, list) or not tasks or any(not isinstance(task, dict) for task in tasks):
        raise ValueError("index must contain a non-empty list of task objects")
    if not isinstance(index.get("aliases"), dict):
        raise ValueError("index aliases must be an object")
    if any(not isinstance(task.get("keywords"), list) for task in tasks):
        raise ValueError("every task must have a keywords list")
    if not isinstance(index.get("models", {}), dict):
        raise ValueError("index models must be an object")
    settings = index.get("settings", {})
    if not isinstance(settings, dict):
        raise ValueError("index settings must be an object")

    prompt_tokens = tokenize(prompt)
    weights = _keyword_weights(tasks)
    scores: list[float] = []
    matches: list[list[dict[str, Any]]] = []
    for task in tasks:
        task_matches: list[dict[str, Any]] = []
        score = 0.0
        seen: set[tuple[str, ...]] = set()
        for keyword in task.get("keywords", []):
            if not isinstance(keyword, str):
                continue
            key = _term_key(keyword)
            if key and key not in seen and _contains_phrase(prompt_tokens, key):
                seen.add(key)
                weight = weights.get(key, 1.0)
                score += weight
                task_matches.append({"keyword": keyword, "weight": round(weight, 4)})
        scores.append(score)
        matches.append(task_matches)

    temperature = float(settings.get("confidence_temperature", 1.0))
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("settings.confidence_temperature must be greater than zero")
    confidences = _softmax(scores, temperature)
    order = sorted(range(len(tasks)), key=lambda position: (-scores[position], position))
    matched_order = [position for position in order if scores[position] > 0]
    candidates = [
        {
            "task_id": tasks[position].get("id"),
            "tier": tasks[position].get("tier"),
            "score": round(scores[position], 4),
            "confidence": round(confidences[position], 4),
            "matched_keywords": matches[position],
        }
        for position in matched_order[:3]
    ]

    if matched_order:
        best = matched_order[0]
        next_confidence = confidences[order[1]] if len(order) > 1 else 0.0
        confidence = confidences[best]
        margin = confidence - next_confidence
        minimum_confidence = float(settings.get("minimum_route_confidence", 0.55))
        minimum_margin = float(settings.get("minimum_route_margin", 0.15))
        selected = (tasks[best] if confidence >= minimum_confidence and margin >= minimum_margin
                    else None)
        candidate_id = tasks[best].get("id")
        selected_confidence = confidence
        selected_margin = margin
        if selected is None:
            classification_status = "needs_review"
            classification_reason = "weak_or_ambiguous_keyword_evidence"
        else:
            classification_status = "routed"
            classification_reason = "keyword_evidence_above_thresholds"
    else:
        selected = None
        candidate_id = None
        selected_confidence = 0.0
        selected_margin = 0.0
        classification_status = "needs_review"
        classification_reason = "no_keyword_evidence"

    default_tier = settings.get("default_tier", "standard_coding")
    primary_tier = selected.get("tier") if selected else default_tier
    if primary_tier not in index.get("aliases", {}):
        raise ValueError(f"recommended tier {primary_tier!r} has no model alias")

    chars_per_token = float(settings.get("chars_per_token", 4.0))
    if not math.isfinite(chars_per_token) or chars_per_token <= 0:
        raise ValueError("settings.chars_per_token must be greater than zero")
    chosen_tier = primary_tier
    chosen_model = _model_for_tier(index, chosen_tier, runtime)
    no_model_request = _is_no_model_call(chosen_tier, chosen_model)
    token_limit = int(settings.get("token_budget_per_task", 15000))
    if no_model_request:
        input_estimate = output_estimate = total_estimate = 0
    else:
        input_estimate = max(1, math.ceil(len(prompt.strip()) / chars_per_token))
        requested_output_tokens = int(settings.get("estimated_output_tokens", 1000))
        output_estimate = min(requested_output_tokens, max(0, token_limit - input_estimate))
        total_estimate = input_estimate + output_estimate
    configured_budget = settings.get("max_cost_per_task_usd")
    max_cost = budget_usd if budget_usd is not None else configured_budget
    if max_cost is not None:
        max_cost = float(max_cost)
        if not math.isfinite(max_cost) or max_cost < 0:
            raise ValueError("budget must be a finite, non-negative USD amount")

    cost, context_fits = _cost_for_tier(index, chosen_tier, input_estimate,
                                        output_estimate, total_estimate, chosen_model, runtime)
    budget_status = "price_unknown" if cost is None else "estimated_within_budget"
    cost_fallback_from = None
    decision = classification_status
    decision_reason = classification_reason

    if not no_model_request and (input_estimate > token_limit or output_estimate < 1):
        chosen_tier = None
        chosen_model = None
        cost = None
        budget_status = "token_budget_exceeded"
        decision = "blocked_by_token_budget"
        decision_reason = "estimated_input_does_not_fit_configured_token_budget"
    elif not context_fits:
        task_fallbacks = selected.get("fallback", []) if selected else []
        compatible: list[tuple[float | None, int, str, str | None]] = []
        for position, tier in enumerate(dict.fromkeys(task_fallbacks)):
            if tier not in index.get("aliases", {}):
                continue
            model = _model_for_tier(index, tier, runtime)
            alternative_cost, fits = _cost_for_tier(
                index, tier, input_estimate, output_estimate, total_estimate, model, runtime)
            within_budget = (max_cost is None or
                             (alternative_cost is not None and alternative_cost <= max_cost))
            if fits and within_budget:
                compatible.append((alternative_cost, position, tier, model))
        if compatible:
            alternative_cost, _, chosen_tier, chosen_model = min(
                compatible, key=lambda item: item[1])
            cost_fallback_from = primary_tier
            cost = alternative_cost
            budget_status = "context_fallback_selected" if cost is not None else "price_unknown"
            decision_reason = "primary_model_context_too_small_fallback_fits"
        else:
            chosen_tier = None
            chosen_model = None
            cost = None
            budget_status = "model_context_too_small_no_verified_fallback"
            decision = "blocked_by_context_limit"
            decision_reason = "no_listed_fallback_fits_context_and_budget"
    elif cost is None and max_cost is not None and not no_model_request and decision == "routed":
        decision = "budget_unknown"
        decision_reason = "price_data_missing_budget_cannot_be_verified"
    elif cost is not None and max_cost is not None and cost > max_cost:
        task_fallbacks = selected.get("fallback", []) if selected else []
        alternatives = list(dict.fromkeys(task_fallbacks))
        affordable: list[tuple[float, int, str, str | None]] = []
        for position, tier in enumerate(alternatives):
            if tier not in index.get("aliases", {}):
                continue
            model = _model_for_tier(index, tier, runtime)
            alternative_cost, fits = _cost_for_tier(
                index, tier, input_estimate, output_estimate, total_estimate, model, runtime)
            if fits and alternative_cost is not None and alternative_cost <= max_cost:
                affordable.append((alternative_cost, position, tier, model))
        if affordable:
            alternative_cost, _, chosen_tier, chosen_model = min(affordable)
            cost_fallback_from = primary_tier
            cost = alternative_cost
            budget_status = "fallback_selected"
            decision_reason = "primary_model_exceeds_budget_fallback_fits"
        else:
            chosen_tier = None
            chosen_model = None
            cost = None
            budget_status = "budget_exceeded_no_affordable_fallback"
            decision = "blocked_by_budget"
            decision_reason = "no_listed_fallback_has_known_cost_within_budget"

    final_no_model_call = chosen_tier is not None and _is_no_model_call(chosen_tier, chosen_model)
    if final_no_model_call:
        budget_status = "no_model_call"
        input_estimate = output_estimate = total_estimate = 0

    selected_id = selected.get("id") if selected else None
    return {
        "decision": decision,
        "reason": decision_reason,
        "requires_human_review": decision != "routed",
        "task_id": selected_id,
        "candidate_task_id": candidate_id,
        "tier": chosen_tier,
        "model": chosen_model,
        "runtime": runtime,
        "confidence": round(selected_confidence, 4),
        "confidence_semantics": "softmax over handcrafted keyword scores; not a calibrated probability",
        "confidence_margin": round(selected_margin, 4),
        "thresholds": {
            "minimum_confidence": float(settings.get("minimum_route_confidence", 0.55)),
            "minimum_margin": float(settings.get("minimum_route_margin", 0.15)),
        },
        "candidates": candidates,
        "directive": selected.get("directive") if selected else None,
        "tools": selected.get("tools", []) if selected else [],
        "fallback_tiers": selected.get("fallback", []) if selected else [],
        "budget": {
            "maximum_cost_usd": max_cost,
            "estimated_cost_usd": round(cost, 8) if cost is not None else None,
            "status": budget_status,
            "fallback_from_tier": cost_fallback_from,
            "estimated_prompt_tokens": input_estimate,
            "estimated_completion_tokens": output_estimate,
            "estimated_total_tokens": total_estimate,
            "token_limit": token_limit,
            "within_token_limit": input_estimate <= token_limit,
            "estimate_method": ("not applicable: no model call" if final_no_model_call else
                                "prompt characters divided by configurable chars_per_token; rough heuristic"),
        },
        "privacy": "router does not transmit or persist prompts; shell/process logging depends on invocation, so prefer stdin for sensitive text",
    }


def _read_prompt(values: list[str], parser: argparse.ArgumentParser) -> str:
    if values:
        return " ".join(values)
    if not sys.stdin.isatty():
        return sys.stdin.read()
    parser.error("provide a prompt as an argument or pipe it through stdin")
    raise AssertionError("argparse.error should exit")


def _print_human(result: dict[str, Any]) -> None:
    print(f"Decision: {result['decision']} ({result['reason']})")
    task = result["task_id"] or result["candidate_task_id"] or "unclassified"
    print(f"Task: {task}")
    print(f"Tier: {result['tier'] or 'none — review budget/context before execution'}")
    print(f"Model: {result['model'] or 'none'}")
    if result["candidate_task_id"]:
        print(f"Routing confidence: {result['confidence']:.0%} — heuristic, not a calibrated probability")
        signals = result["candidates"][0]["matched_keywords"]
        print("Signals: " + ", ".join(item["keyword"] for item in signals))
    budget = result["budget"]
    cost = budget["estimated_cost_usd"]
    cost_text = f"${cost:.8f}" if cost is not None else "unknown (no matching per-input/output price data)"
    print(f"Estimated cost: {cost_text} [{budget['status']}]")
    print("Token estimate: ~{estimated_prompt_tokens} input + {estimated_completion_tokens} output "
          "(limit {token_limit}; approximate)".format(**budget))
    if result["fallback_tiers"]:
        print("Fallback tiers: " + " → ".join(result["fallback_tiers"]))
    if result["directive"]:
        print("Directive: " + result["directive"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="*", help="prompt text; omit to read stdin")
    parser.add_argument("--index", type=Path, default=INDEX, help="path to index.json")
    parser.add_argument("--runtime", choices=("generic", "claude_code"), default="generic",
                        help="choose generic or Claude Code model aliases")
    parser.add_argument("--budget", type=float, help="override max request cost in USD")
    parser.add_argument("--json", action="store_true", help="print structured JSON (no prompt text)")
    args = parser.parse_args(argv)
    prompt = _read_prompt(args.prompt, parser)
    try:
        index = json.loads(args.index.read_text(encoding="utf-8"))
        result = route_prompt(prompt, index, runtime=args.runtime, budget_usd=args.budget)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"[meta-skill] error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
