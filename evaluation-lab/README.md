# Reproducible Routing Evaluation Lab

A dependency-free evaluation harness for comparing task routers and model-selection policies against a labelled test set. Designed to complement `meta-skill`: it measures classification quality and abstention behavior without claiming that a heuristic score is a calibrated probability.

## Why this exists

A router that selects a model or workflow should be evaluated on held-out labelled cases, not judged from a few attractive demos. This harness reports overall and per-class behavior, confusion counts, coverage, selective accuracy, abstention, and—when complete probability vectors are supplied—multiclass Brier score and expected calibration error (ECE).

## Quick start

Requires Python 3.11+; standard library only.

```bash
python3 evaluation-lab/evaluate.py \
  --gold evaluation-lab/fixtures/gold.jsonl \
  --predictions evaluation-lab/fixtures/predictions.jsonl \
  --out evaluation-lab/report.json
python3 -m unittest discover -s evaluation-lab/tests -v
```

The example fixture is intentionally tiny and synthetic. Its metrics demonstrate the output format only; they are not evidence of real-world performance.

## Input format

One JSON object per line. The gold file requires unique `id` and `label` fields:

```json
{"id":"case-001","label":"testing"}
```

Predictions require matching IDs and a `label`. Use `abstain` when the router declines to make a recommendation. Optional `confidence` must be between 0 and 1. Optional `probabilities` must provide a probability for every class and sum to 1 (within tolerance).

```json
{"id":"case-001","label":"testing","confidence":0.82}
```

The evaluator rejects duplicate IDs, missing/extra predictions, malformed rows, unknown labels, invalid confidence, and incomplete or invalid probability vectors. It never silently drops cases.

## Metrics

- **Accuracy:** correct predictions / all labelled cases; abstentions count as incorrect.
- **Macro-F1:** unweighted mean of per-class F1, including classes with zero predicted examples.
- **Coverage:** fraction receiving a non-abstaining prediction.
- **Selective accuracy:** accuracy among non-abstained cases; null if coverage is zero.
- **Abstention rate:** fraction labelled `abstain`.
- **Confusion matrix:** gold labels by predicted labels, including the `abstain` column.
- **Brier score:** multiclass mean squared error between probability vectors and one-hot gold labels; lower is better.
- **ECE:** confidence-bin weighted gap between mean confidence and empirical accuracy; lower is better, but binning makes it sample-size-sensitive.

Confidence is not treated as a probability unless a full probability vector is provided. ECE and Brier are omitted when probability vectors are absent. No statistical confidence intervals are reported for the tiny demo fixture.

## Fair evaluation protocol

1. Freeze the label taxonomy and record how ambiguous examples are labelled.
2. Separate development data from a held-out test set before tuning thresholds.
3. Include difficult, ambiguous, multilingual, out-of-domain, and adversarial examples.
4. Compare against simple baselines (majority class, keyword baseline, and current router).
5. Report per-class metrics and coverage/quality trade-offs, not accuracy alone.
6. Keep real user prompts out of public fixtures unless consent and privacy review explicitly permit them. Prefer synthetic or carefully redacted cases.
7. Record dataset version, router version, commit SHA, and evaluation command with each published result.
8. Never describe synthetic smoke results as production accuracy, calibrated confidence, cost savings, or model quality.

## Integration

Export one prediction JSONL row per gold case from the router under test, preserving the stable case ID. For example, run your router on each `input` field in a private evaluation adapter and write only the predicted class, confidence, and optional probability vector. Keep sensitive prompts and private datasets outside Git.

## Scope and limitations

This is a small offline measurement tool, not a model, production telemetry system, statistical significance package, or security certification. A well-scoring test set can still be unrepresentative. Review the methodology before using the numbers to make release or cost decisions.
