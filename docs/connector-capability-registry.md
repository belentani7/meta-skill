# BELENTANI — Connector Capability Registry

Updated: 2026-11-15. This document is a **snapshot**, not an authorization token or a guarantee of ongoing access.

## Composio connections verified in this session

| Toolkit | Connection | Safe integration target |
| --- | --- | --- |
| GitHub | Active | Repository inventory, branches, draft PRs, CI metadata |
| Google Drive | Active | Versioned reports, model manifests, generated artifacts |
| Gmail | Active | Opt-in notifications and project-specific mail triage |
| Figma | Active | Design-system metadata and review handoffs |
| Meta Ads | Active | Read-only campaign analytics, where permitted |

Other toolkits are **not assumed authorized**. Request individual OAuth approval through the official connection flow before using them. Never bypass a connector's enhanced controls.

## GitHub integration contract

1. Discover the exact target repository and its existing conventions before proposing files.
2. Use read-only inspection first. Route findings to the relevant repository, not every repository.
3. Work on a feature branch and open a **draft** pull request; do not force-push or merge automatically.
4. Add a narrowly scoped test or validation plan for each change.
5. Do not ingest Gmail messages, Drive documents, Figma private files, tokens, cookies, customer records or advertising data into GitHub.
6. Do not commit API keys, model weights, private media, copyrighted assets without rights, or generated secrets.
7. Store only sanitized, non-sensitive summaries in repository documentation.
8. Respect API quotas, free-tier limits and existing production deployments.
9. Require explicit approval for OAuth, billable compute, security-setting changes, and destructive operations.

## Project routing

- `meta-skill`: connector discovery, cost-aware routing, evaluation harness, policy checks.
- `secure-t`: isolated educational labs and security curriculum, not live credentials.
- `belentani.es`: artist-facing UX and approved public assets; no private sessions or audio stems.
- `BELENTANI GENESIS` (dedicated repo when established): ACE-Step, ComfyUI, media pipelines and GPU workers.
- `unified-os-v2`: integrate only after verifying the current canonical repository and its actual routing contracts.

## Proposed machine-readable metadata

A future registry may track `toolkit`, `status`, `last_verified_at`, `allowed_scopes`, `destination_repo`, `data_classification`, `estimated_cost`, `approval_required`, and `health_check`. Never store OAuth credentials in that registry.

## Next verification gates

- Confirm GitHub repository inventory count and pagination.
- Confirm connector-specific scopes and token expiration before scheduled use.
- Execute a read-only smoke test for each active connector.
- Propose repo-specific draft PRs only when tests and source inspection justify changes.
