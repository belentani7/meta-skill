# Changelog

## 1.1.0 — 2026-10-11

- Added an offline, explainable CLI router for multilingual task matching, abstention, tier resolution, rough token estimates, model context checks, and cost ceilings when exact input/output rates are known.
- Expanded the task catalog from 8 to 12 archetypes, including general software work, research, writing/translation, and mathematical reasoning.
- Added a synthetic multilingual smoke set and an offline evaluator for coverage, classification metrics, Brier score, and expected calibration error; explicitly disclaims generalization from this hand-curated set.
- Added `estimate_savings.py` to compare task-tier routing with a fixed-model baseline using aggregate request/token data and exact catalog rates; unknown pricing never becomes zero.
- Strengthened index validation and updater tests; missing or malformed rates remain unknown rather than being treated as free.
- Changed model refresh to pin selected aliases by default. Candidate discovery is not a quality benchmark; `--promote-newest` is an explicit override.
- Documented current routing research, pricing limits, confidence semantics, and the path toward privacy-preserving evaluation.
- Removed third-party animation CDNs from the landing page and repaired mojibake/BOMs in the magic-kit Markdown.

## 1.0.0 — 2026-07-19

First public release.

- Routing protocol (`SKILL.md`) with 4 stable tiers and budget guard.
- Universal index (`index.json`): 8 task archetypes, ES/EN keywords, fallbacks.
- Updater (`update_models.py`): OpenRouter public API, no key, stdlib only, atomic writes, offline-safe, `--validate`, text-model filter, local tier protected.
- Tests (unittest, stdlib) + CI (Linux & Windows).
