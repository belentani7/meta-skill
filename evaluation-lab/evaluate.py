#!/usr/bin/env python3
"""Dependency-free evaluator for labelled routing predictions."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ABSTAIN = "abstain"
TOLERANCE = 1e-6


class EvaluationError(ValueError):
    """Raised when input data cannot be evaluated without ambiguity."""


def load_jsonl(path: str | Path, *, kind: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        stream = Path(path).open("r", encoding="utf-8")
    except OSError as exc:
        raise EvaluationError(f"cannot open {kind} file {path}: {exc}") from exc
    with stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise EvaluationError(f"{kind}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise EvaluationError(f"{kind}:{line_number}: each row must be a JSON object")
            case_id = row.get("id")
            if not isinstance(case_id, str) or not case_id.strip():
                raise EvaluationError(f"{kind}:{line_number}: id must be a non-empty string")
            if case_id in seen:
                raise EvaluationError(f"{kind}:{line_number}: duplicate id {case_id!r}")
            seen.add(case_id)
            rows.append(row)
    if not rows:
        raise EvaluationError(f"{kind}: file contains no data rows")
    return rows


def _f1(tp: int, fp: int, fn: int) -> float:
    denominator = 2 * tp + fp + fn
    return 0.0 if denominator == 0 else (2 * tp) / denominator


def evaluate(gold_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]], *, bins: int = 10) -> dict[str, Any]:
    if not 1 <= bins <= 100:
        raise EvaluationError("bins must be between 1 and 100")

    gold: dict[str, str] = {}
    for row in gold_rows:
        label = row.get("label")
        if not isinstance(label, str) or not label.strip() or label == ABSTAIN:
            raise EvaluationError(f"gold row {row.get('id')!r}: label must be a non-empty class other than {ABSTAIN!r}")
        gold[row["id"]] = label

    predictions: dict[str, dict[str, Any]] = {}
    for row in prediction_rows:
        label = row.get("label")
        if not isinstance(label, str) or not label.strip():
            raise EvaluationError(f"prediction row {row.get('id')!r}: label must be a non-empty string")
        predictions[row["id"]] = row

    missing = sorted(set(gold) - set(predictions))
    extra = sorted(set(predictions) - set(gold))
    if missing or extra:
        pieces = []
        if missing:
            pieces.append(f"missing predictions for {missing[:10]}")
        if extra:
            pieces.append(f"predictions without gold labels {extra[:10]}")
        raise EvaluationError("; ".join(pieces))

    classes = sorted(set(gold.values()))
    allowed_predictions = set(classes) | {ABSTAIN}
    for case_id, row in predictions.items():
        label = row["label"]
        if label not in allowed_predictions:
            raise EvaluationError(f"prediction {case_id!r}: unknown label {label!r}; expected one of {sorted(allowed_predictions)}")
        if "confidence" in row:
            confidence = row["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise EvaluationError(f"prediction {case_id!r}: confidence must be a finite number in [0, 1]")
        if "probabilities" in row:
            probs = row["probabilities"]
            if not isinstance(probs, dict) or set(probs) != set(classes):
                raise EvaluationError(f"prediction {case_id!r}: probabilities must contain exactly these classes: {classes}")
            for cls, value in probs.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                    raise EvaluationError(f"prediction {case_id!r}: probability for {cls!r} must be finite and in [0, 1]")
            if abs(sum(probs.values()) - 1.0) > TOLERANCE:
                raise EvaluationError(f"prediction {case_id!r}: probabilities must sum to 1 (tolerance {TOLERANCE})")
        if "probabilities" in row and "confidence" in row:
            max_probability = max(row["probabilities"].values())
            if abs(float(row["confidence"]) - max_probability) > 0.05:
                raise EvaluationError(f"prediction {case_id!r}: confidence conflicts with maximum class probability")

    total = len(gold)
    correct = sum(predictions[case_id]["label"] == expected for case_id, expected in gold.items())
    covered_ids = [case_id for case_id in gold if predictions[case_id]["label"] != ABSTAIN]
    covered_correct = sum(predictions[case_id]["label"] == gold[case_id] for case_id in covered_ids)
    matrix = {actual: {predicted: 0 for predicted in classes + [ABSTAIN]} for actual in classes}
    for case_id, actual in gold.items():
        matrix[actual][predictions[case_id]["label"]] += 1

    per_class: dict[str, dict[str, float | int]] = {}
    f1_values = []
    for cls in classes:
        tp = matrix[cls][cls]
        fp = sum(matrix[other][cls] for other in classes if other != cls)
        fn = sum(matrix[cls][other] for other in classes + [ABSTAIN] if other != cls)
        support = sum(matrix[cls].values())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / support if support else 0.0
        f1 = _f1(tp, fp, fn)
        f1_values.append(f1)
        per_class[cls] = {
            "support": support,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }

    result: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_size": total,
        "class_labels": classes,
        "metrics": {
            "accuracy": round(correct / total, 6),
            "macro_f1": round(sum(f1_values) / len(f1_values), 6),
            "coverage": round(len(covered_ids) / total, 6),
            "selective_accuracy": round(covered_correct / len(covered_ids), 6) if covered_ids else None,
            "abstention_rate": round((total - len(covered_ids)) / total, 6),
        },
        "per_class": per_class,
        "confusion_matrix": matrix,
        "calibration": None,
        "limitations": [
            "Metrics describe only the supplied labelled dataset.",
            "Confidence values alone are not assumed to be calibrated probabilities.",
            "A small or unrepresentative test set can produce misleading results.",
        ],
    }

    probability_rows = [predictions[case_id] for case_id in gold if "probabilities" in predictions[case_id]]
    if probability_rows and len(probability_rows) != total:
        raise EvaluationError("probabilities must be supplied for every prediction or for none; mixed calibration data is not comparable")
    if probability_rows:
        brier_sum = 0.0
        calibration_items = []
        for case_id, actual in gold.items():
            row = predictions[case_id]
            probs = row["probabilities"]
            brier_sum += sum((float(probs[cls]) - (1.0 if cls == actual else 0.0)) ** 2 for cls in classes)
            confidence = float(row.get("confidence", max(probs.values())))
            predicted = row["label"]
            calibration_items.append((confidence, predicted == actual))
        ece = 0.0
        bin_rows = []
        for index in range(bins):
            lower = index / bins
            upper = (index + 1) / bins
            members = [(conf, hit) for conf, hit in calibration_items if lower <= conf < upper or (index == bins - 1 and conf == 1.0)]
            if members:
                mean_confidence = sum(conf for conf, _ in members) / len(members)
                observed_accuracy = sum(hit for _, hit in members) / len(members)
                ece += len(members) / total * abs(mean_confidence - observed_accuracy)
                bin_rows.append({
                    "lower": round(lower, 4),
                    "upper": round(upper, 4),
                    "count": len(members),
                    "mean_confidence": round(mean_confidence, 6),
                    "accuracy": round(observed_accuracy, 6),
                })
        result["calibration"] = {
            "brier_score": round(brier_sum / total, 6),
            "expected_calibration_error": round(ece, 6),
            "bins": bins,
            "bin_details": bin_rows,
            "note": "Calibration metrics are descriptive and sensitive to sample size and binning.",
        }
    return result


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Routing evaluation report",
        "",
        f"- Dataset size: **{report['dataset_size']}**",
        f"- Classes: {', '.join(report['class_labels'])}",
        f"- Accuracy: **{metrics['accuracy']:.3f}**",
        f"- Macro-F1: **{metrics['macro_f1']:.3f}**",
        f"- Coverage: **{metrics['coverage']:.3f}**",
        f"- Selective accuracy: **{'n/a' if metrics['selective_accuracy'] is None else format(metrics['selective_accuracy'], '.3f')}**",
        f"- Abstention rate: **{metrics['abstention_rate']:.3f}**",
        "",
        "## Per-class metrics",
        "",
        "| Class | Support | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, values in report["per_class"].items():
        lines.append(f"| {label} | {values['support']} | {values['precision']:.3f} | {values['recall']:.3f} | {values['f1']:.3f} |")
    if report["calibration"] is not None:
        calibration = report["calibration"]
        lines.extend(["", "## Calibration", "", f"- Brier score: **{calibration['brier_score']:.3f}**", f"- ECE: **{calibration['expected_calibration_error']:.3f}**"])
    lines.extend(["", "> These results describe only the supplied dataset. Do not interpret synthetic fixture metrics as production performance.", ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True, help="gold JSONL file with id and label")
    parser.add_argument("--predictions", required=True, help="prediction JSONL file with id and label")
    parser.add_argument("--out", help="write JSON report to this path; stdout if omitted")
    parser.add_argument("--markdown", help="optional Markdown report path")
    parser.add_argument("--bins", type=int, default=10, help="ECE bins (1-100; default 10)")
    args = parser.parse_args(argv)
    try:
        report = evaluate(load_jsonl(args.gold, kind="gold"), load_jsonl(args.predictions, kind="predictions"), bins=args.bins)
    except EvaluationError as exc:
        print(f"evaluation error: {exc}", file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
