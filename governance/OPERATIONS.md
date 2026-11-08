# Operations and evidence runbook

## Lifecycle
Observe -> classify -> propose -> sandbox test -> independent review -> release -> post-deploy verify.

## Incident
Record incident ID, affected service, observed symptoms, time window and evidence. Redact sensitive telemetry. Identify blast radius, stop automated retries, and assess whether data protection escalation is necessary. Generate repair only on an isolated branch. Run targeted tests, golden evaluation and security checks. Request human review for deployment, secrets, permissions, destructive operations and production data. After release, test the real production endpoint and observe error rates; revert through an approved mechanism if the predefined success metric fails.

## Evaluation
Store labeled representative examples, baseline version, sample size, uncertainty, abstention rate, regressions and observed costs. Synthetic smoke datasets must not be presented as production accuracy. Do not use a p-value alone as a release gate.

## Privacy
For each product, assess applicable EU AI Act and GDPR duties, data flows, processors, retention and incident reporting. A template is not proof of legal compliance. Do not include raw prompts or PII in public artifacts.

## Evidence labels
- source: repository and commit identified
- tested: exact CI run and suite identified
- built: immutable artifact digest identified
- deployed: environment and version identified
- production-verified: timestamped live smoke check identified

Never infer a higher evidence level from a lower one.
