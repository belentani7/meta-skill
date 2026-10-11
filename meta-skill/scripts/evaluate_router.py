#!/usr/bin/env python3
"""Run an offline labeled evaluation set against the keyword router.

Results describe only the supplied dataset. Use representative, consented,
held-out data before making claims about real-world accuracy or savings.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from route import INDEX, route_prompt

DEFAULT_DATASET = Path(__file__).resolve().parent.parent / "evaluations" / "smoke.json"
ABSTAIN = "<abstain>"


def _macro_f1(labels: list[str], expected: list[str | None], predicted: list[str | None]) -> float:
    scores: list[float] = []
    for label in labels:
        true_positive = sum(actual == label and guess == label
                            for actual, guess in zip(expected, predicted))
        false_positive = sum(actual != label and guess == label
                             for actual, guess in zip(expected, predicted))
        false_negative = sum(actual == label and guess != label
                             for actual, guess in zip(expected, predicted))
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(2 * true_positive / denominator if denominator else 0.0)
    return sum(scores) / len(scores) if scores else 0.0


def _calibration_summary(confidences: list[float], correctness: list[bool],
                         bins: int = 5) -> dict[str, Any]:
    if not confidences:
        return {"sample_count": 0, "brier_score": None, "expected_calibration_error": None,
                "bins": []}
    brier = sum((confidence - int(correct)) ** 2
                for confidence, correct in zip(confidences, correctness)) / len(confidences)
    rows = []
    ece = 0.0
    for number in range(bins):
        lower = number / bins
        upper = (number + 1) / bins
        members = [i for i, confidence in enumerate(confidences)
                   if lower <= confidence < upper or (number == bins - 1 and confidence == 1.0)]
        if not members:
            continue
        mean_confidence = sum(confidences[i] for i in members) / len(members)
        observed_accuracy = sum(correctness[i] for i in members) / len(members)
        ece += len(members) / len(confidences) * abs(mean_confidence - observed_accuracy)
        rows.append({
            "lower_bound": round(lower, 2),
            "upper_bound": round(upper, 2),
            "count": len(members),
            "mean_confidence": round(mean_confidence, 4),
            "observed_accuracy": round(observed_accuracy, 4),
        })
    return {
        "sample_count": len(confidences),
        "brier_score": round(brier, 4),
        "expected_calibration_error": round(ece, 4),
        "bins": rows,
    }


def evaluate_cases(cases: list[dict[str, Any]], index: dict[str, Any]) -> dict[str, Any]:
    """Compute task-classification and selective-confidence metrics."""
    if not cases:
        raise ValueError("evaluation dataset must contain at least one case")
    known_tasks = {task.get("id") for task in index.get("tasks", [])}
    expected: list[str | None] = []
    predicted: list[str | None] = []
    confidences: list[float] = []
    correctness: list[bool] = []
    classified = 0
    confusion: dict[str, dict[str, int]] = {}
    for number, case in enumerate(cases, start=1):
        if not isinstance(case, dict) or not isinstance(case.get("prompt"), str):
            raise ValueError(f"case {number} must contain a string prompt")
        actual = case.get("expected")
        if actual is not None and actual not in known_tasks:
            raise ValueError(f"case {number} has unknown expected task {actual!r}")
        result = route_prompt(case["prompt"], index)
        guess = result["task_id"]
        expected.append(actual)
        predicted.append(guess)
        row = confusion.setdefault(actual or ABSTAIN, {})
        row[guess or ABSTAIN] = row.get(guess or ABSTAIN, 0) + 1
        if guess is not None:
            classified += 1
            confidences.append(float(result["confidence"]))
            correctness.append(guess == actual)

    total = len(cases)
    correct = sum(actual == guess for actual, guess in zip(expected, predicted))
    labels = sorted(label for label in known_tasks if label in expected)
    covered_correct = sum(actual == guess for actual, guess in zip(expected, predicted)
                          if guess is not None)
    return {
        "case_count": total,
        "coverage": round(classified / total, 4),
        "accuracy_including_abstentions": round(correct / total, 4),
        "selective_accuracy": round(covered_correct / classified, 4) if classified else None,
        "macro_f1": round(_macro_f1(labels, expected, predicted), 4),
        "abstentions": total - classified,
        "confidence_calibration_on_classified_cases": _calibration_summary(confidences, correctness),
        "confusion_matrix": confusion,
        "interpretation": "smoke-set metrics only; not a production accuracy, cost-savings, or probability claim",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET,
                        help="JSON file with {cases:[{prompt, expected}, ...]}")
    parser.add_argument("--index", type=Path, default=INDEX, help="path to index.json")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        index = json.loads(args.index.read_text(encoding="utf-8"))
        dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
        cases = dataset["cases"] if isinstance(dataset, dict) else dataset
        if not isinstance(cases, list):
            raise ValueError("evaluation file must contain a list of cases")
        report = evaluate_cases(cases, index)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"[meta-skill] evaluation error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        calibration = report["confidence_calibration_on_classified_cases"]
        print("Meta-Skill offline smoke evaluation")
        print(f"Cases: {report['case_count']}; coverage: {report['coverage']:.1%}; "
              f"accuracy: {report['accuracy_including_abstentions']:.1%}; "
              f"selective accuracy: {report['selective_accuracy']}")
        print(f"Macro-F1: {report['macro_f1']:.4f}; abstentions: {report['abstentions']}")
        print(f"Calibration sample: {calibration['sample_count']} classified cases; "
              f"Brier: {calibration['brier_score']}; ECE: {calibration['expected_calibration_error']}")
        print("Note: these figures describe only this labeled dataset; do not generalize them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
