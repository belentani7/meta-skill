# Contributing

PRs welcome. Keep it simple:

1. Data lives in `meta-skill/index.json` (tasks, tiers, regex patterns). Most contributions only touch this file.
2. `meta-skill/SKILL.md` holds the protocol — change it for behavior only, never to add model names.
3. Before opening a PR, both must pass (stdlib only, no installs):

```bash
python -m unittest
python meta-skill/scripts/update_models.py --validate
```

MIT — by BELENTANI.
