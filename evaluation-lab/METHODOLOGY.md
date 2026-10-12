# Evaluation methodology and decision record

## Purpose

This directory supplies a small, auditable measurement layer for task routers. It does not alter routing decisions, select a provider, call a model, or collect user traffic.

## Contract

- The gold set is the source of truth for the expected class.
- Every gold ID must have exactly one prediction.
- Unknown classes and malformed probability vectors are hard errors.
- `abstain` is an explicit prediction outcome. It reduces coverage and counts as incorrect for overall accuracy.
- Selective accuracy is calculated only among covered examples and is always shown alongside coverage.
- Calibration metrics are calculated only when every prediction has a full class probability vector.
- The tool does not infer a confidence score from keywords or turn a heuristic score into a probability.

## Reproducibility checklist

For any result intended for a portfolio, release, or hiring review, record:

- repository commit SHA and router version;
- dataset version and source/consent status;
- class definitions and annotation guidance;
- split policy and whether the test set was held out before tuning;
- evaluation command and Python version;
- per-class metrics, coverage, confusion matrix, and calibration metrics where justified;
- known limitations and any material distribution shift.

## Threats to validity

- **Selection bias:** hand-picked examples can exaggerate performance.
- **Leakage:** using test cases to tune thresholds invalidates the held-out estimate.
- **Label ambiguity:** disagreement between annotators can look like model error.
- **Class imbalance:** aggregate accuracy may hide a weak minority class.
- **Calibration sample size:** ECE is unstable on small datasets and depends on bin boundaries.
- **Distribution shift:** multilingual, adversarial, and novel tasks may behave differently from the test set.
- **Synthetic data:** fixtures test the evaluator contract, not production quality.

## Release-gate guidance

Do not set a single universal accuracy threshold. Define minimum per-class recall, maximum abstention, acceptable cost/latency, and hard safety constraints for the specific application. Keep security policy failures as hard blockers rather than allowing them to be offset by a high average score. Require human review for high-impact or out-of-distribution cases.

The sample files in `fixtures/` are synthetic examples only. They must not be cited as measured performance of Meta-Skill or any model.
