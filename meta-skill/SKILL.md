---
name: meta-skill
description: >-
  Offline, explainable router and token-budget advisor for coding and multi-step
  work. Use first to classify software, research, writing, testing, data, and
  security tasks; recommend a model tier; explain uncertainty; and delegate to
  a more specific installed skill. Also use for model selection and cost control.
  No prompt is sent to an API by this skill. The optional OpenRouter catalog
  updater only fetches public model metadata and needs no API key.
---

# Meta-Skill — Universal Router

Model names change; task types and routing policy should not. Dated model IDs
belong in `index.json`, never in this protocol.

## Protocol

1. Read `index.json` from this skill's directory. When Python is available, use
   `scripts/route.py --json` with the request on stdin for the reproducible
   keyword match, relative confidence, tier, and budget status. The router is
   offline: it neither transmits nor saves the prompt. If Python is unavailable,
   apply the same task keywords and thresholds manually.
2. Treat the router result honestly:
   - `routed`: use the selected task/tier as a recommendation, then verify that
     the model and tools are actually available.
   - `needs_review`: the evidence is absent or ambiguous. Do not silently turn
     an unknown request into `quick_fix`; use the configured default tier or
     ask one clarifying question when the ambiguity matters.
   - `budget_unknown`: price data is missing, so the configured cost ceiling
     cannot be verified. Never present an unknown price as zero or “within
     budget”. If the user set a hard cap, pause or choose an alternative with
     known rates.
   - `blocked_by_budget`, `blocked_by_token_budget`, or
     `blocked_by_context_limit`: do not recommend sending the request to that
     model. Explain the constraint and available options.
3. Resolve `task.tier` using `aliases`, or `claude_code_aliases` when the
   installed runtime is Claude Code. Confirm the selected model is available.
   Walk the task's `fallback` list only when a fallback is appropriate and its
   capabilities, context window, and price are verified. A fallback list is an
   allowed alternative/escalation order; it does **not** imply that every entry
   is cheaper than the primary tier.
4. If a more specific installed skill fits the task, delegate to it.
5. Before any model call:
   - Token count is a rough character-based estimate, not the provider tokenizer.
   - Apply the cost ceiling only when separate input/output rates are present
     for the exact selected model and the runtime uses those rates. Otherwise
     mark cost unknown; never substitute a tier-name guess for pricing.
   - Prefer deterministic tools and already-read context when they can safely
     solve the request without another model call.
   - Never re-read files already in context; batch independent tool calls.
6. Execute the task directive and report a concise status, for example:
   `[meta-skill] task=<id|unclassified> tier=<tier|blocked> model=<resolved|none> confidence=<heuristic> est_cost=<usd|unknown>`.
   Call confidence heuristic and uncalibrated; omit a numeric cost if it is
   unknown. Do not claim this skill executed a model request.

## Tiers (stable abstractions)

- `premium_reasoning` — security, research, or high-complexity reasoning.
- `standard_coding` — general engineering, APIs, frontend, data, and DevOps.
- `budget_fast` — routine testing, writing, translation, and simpler tasks.
- `local_zero_token` — only unmistakable, deterministic edits such as a typo or
  whitespace correction; no model call is made.

Task-to-tier mappings, terms, confidence thresholds, token assumptions, model
aliases, and any published pricing are data in `index.json`.

## Local tools

From the repository root:

```bash
python3 meta-skill/scripts/route.py "Build a responsive React component"
python3 meta-skill/scripts/route.py --runtime claude_code --json "Write pytest tests"
printf '%s' "Audit this API for OWASP issues" | python3 meta-skill/scripts/route.py --json
python3 meta-skill/scripts/evaluate_router.py
python3 meta-skill/scripts/estimate_savings.py --workload /path/to/aggregate-workload.json --json
python3 meta-skill/scripts/update_models.py --validate
```

`evaluate_router.py` reports coverage, classification metrics, and calibration
metrics on the supplied labeled cases. The checked-in smoke set is synthetic
and hand-curated; its results are not real-world accuracy, model quality, or
cost-savings claims. A softmax over handmade keyword weights is a ranking score,
not a calibrated probability of correctness. Calibration needs representative,
consented labels and a held-out evaluation set.

`estimate_savings.py` compares the configured task policy (declared fallbacks
and per-request cost limit) with a fixed-tier baseline using aggregate request
counts and average input/output tokens; it does not collect prompts. It is not a
request-by-request replay, and routing at the averages can differ from routing
each request. Exact active-alias prices are required for numeric totals. Provide
observed maximum token counts to check context fit; average-only workloads leave
tail risk. It measures neither answer quality nor actual billing.

To refresh public model metadata, run `python3 meta-skill/scripts/update_models.py`.
It stores distinct prompt and completion prices, filters for text output, and
writes atomically. By default it refreshes candidates but leaves selected model
aliases pinned: release date is not evidence of quality. Manually change an
alias after reviewing its quality, capability, and price. `--promote-newest` is
an explicit, unbenchmarked shortcut. The `local_zero_token` tier is never
updated. A failed request or missing tier match preserves the last known data.
The catalog is not billing data; provider routing, caching, retries, output
length, and runtime-specific rates can change the actual charge.

## Longevity contract

- Never put dated model names in this file.
- Add a task in `index.json` with unique `id`, multilingual `keywords`,
  `complexity`, `tier`, `fallback`, `tools`, and a safe, concise `directive`.
- Update the synthetic evaluation set and add regression tests for every new
  task or matching rule; include ambiguous and unmatched examples.
- Adjust alias patterns as model families change, then validate them against
  both intended matches and false positives.
- Promote a confidence value to a probability only after training and
  calibration against representative, held-out labels.

---
**By BELENTANI** — artist & singer · Neurodivergent, no labels: a gift.
Brasil 🇧🇷 → Barcelona · IG [@BELENTANI_](https://instagram.com/belentani_)
