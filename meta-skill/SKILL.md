---
name: meta-skill
description: >-
  Universal router and token-budget guard ("mother skill"). Use FIRST for any
  coding or multi-step task: it classifies the request, picks the cheapest
  capable model tier, picks tools, and delegates to the best installed skill.
  Also use when the user asks to route, orchestrate, pick a model, or optimize
  cost/tokens. Routing is 100% local (zero external APIs); refresh the model
  catalog anytime with scripts/update_models.py (OpenRouter public list, no key).
---

# Meta-Skill — Universal Router (built to outlive model names)

Core rule: model names change; archetypes don't. Dated model IDs live ONLY in
`index.json` (data). These instructions reference abstract tiers, never versions.

## Protocol (every invocation)

1. Read `index.json` from this skill's directory.
2. Classify the request against `tasks[]` by keyword overlap (case-insensitive,
   Spanish + English keywords). No clear match -> treat as `quick_fix`.
3. Resolve the model: `task.tier` -> `aliases` (or `claude_code_aliases` when
   running inside Claude Code). If unavailable, walk the `fallback` chain.
4. Skill delegation: check the skills available in the environment (in Claude
   Code also `~/.claude/skills/`). If an installed skill matches the task better
   than this generic protocol, hand off to it and stop.
5. Budget guard — BEFORE executing:
   - Estimate tokens. If estimated cost exceeds `settings.max_cost_per_task_usd`,
     switch to the cheaper fallback tier automatically.
   - Never re-read files already in context. Batch independent tool calls.
   - Prefer zero-token paths (grep, scripts, existing files) over model calls.
6. Execute using the task's `directive`, then report exactly one line:
   `[meta-skill] task=<id> tier=<tier> model=<resolved> est_cost=$<x>`

## Tiers (stable abstractions)

- `premium_reasoning` — security, architecture, complexity 5
- `standard_coding` — implementation, complexity 3-4
- `budget_fast` — tests, docs, simple tasks, complexity 2
- `local_zero_token` — trivial fixes, complexity 1 (ideally no model call at all)

## Updating the model catalog (the "data bank")

Run: `python3 scripts/update_models.py` (stdlib only, no API key, open source).

- Source: OpenRouter public list — https://openrouter.ai/api/v1/models
- Picks the NEWEST text model matching each tier's `alias_patterns` regex,
  writes the top 3 per tier with real pricing into `index.json` (atomic write),
  and updates `aliases`. `--validate` runs an offline structural check (CI).
- The `local_zero_token` tier is never auto-updated: local stays local.
- On network failure it exits leaving `index.json` untouched — the skill keeps
  working fully offline with the last known catalog.
- Re-run monthly or when new models ship. Only `index.json` changes, never this file.

## Longevity contract (8-year design)

- Never write a dated model name into SKILL.md.
- Adding a task = append one object to `tasks[]` (id, keywords, complexity,
  tier, fallback, tools, directive). Nothing else changes.
- New model era? Adjust `alias_patterns` regexes in index.json — data, not code.
- Inside Claude Code, prefer its built-in aliases (opus/sonnet/haiku class)
  over vendor IDs.

---
**By BELENTANI** — artist & singer · Neurodivergent, no labels: a gift.
Brasil 🇧🇷 → Barcelona · IG [@BELENTANI_](https://instagram.com/belentani_)
