# Sovereign Evolution — experimental foundation

This branch adds three **offline** primitives, not a deployed autonomous agent:

- `guard.py`: fail-closed policy preflight; must be enforced by the execution boundary. An agent calling tools directly bypasses it.
- `knowledge.py`: typed versioned JSON graph, with explicit provenance supplied by the caller. No automatic repository crawler or semantic GraphRAG retrieval yet.
- `mesh.py`: deterministic quota-based provider selection and local usage snapshots. No provider credentials, network calls, retry/backoff, distributed locking or verified API integrations.
- `repair.py`: proposal-only MAPE-K planning scaffold, never executes patches.

Run `python -m unittest discover -s tests -p 'test_sovereign*.py' -v`.

No claims of zero operating cost, infinite throughput or production security. A local Ollama fallback is possible only if a local runtime is actually available, and its compute/power are not free. Do not merge until CI and threat-model review pass.
