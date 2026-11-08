# Autonomous Engineering Constitution v1

Status: proposed, not enforced globally. Scope: Meta-Skill autonomous changes.

1. Autonomous agents may observe, classify, and propose changes, but must not push directly to production.
2. All generated changes must use an isolated branch and pull request.
3. No agent may edit its own governing policy, credentials, permissions, or approval requirements.
4. No secrets, personal data, or raw prompts may be exported to logs or external model providers by default.
5. No destructive database or infrastructure operations without explicit human authorization.
6. Every change needs a reproducible test plan and a recorded result; a passing build is not production verification.
7. Model, prompt, or router changes require a versioned evaluation baseline and documented quality comparison.
8. Security-sensitive changes require human review, regardless of test outcome.
9. Automation must enforce finite retry limits, timeouts, and spend budgets.
10. Failure or ambiguous evidence must fail closed and produce an actionable report.
11. Release promotion requires separate verification of artifact integrity and real deployment behavior.
12. Incidents, rollbacks, and failed repairs must be recorded with cause and outcome.

This document describes policy. Actual enforcement requires protected branches, restricted tokens, required reviews and independent CI checks. Never treat this file alone as a security boundary.
