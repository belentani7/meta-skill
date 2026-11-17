#!/usr/bin/env python3
"""Read-only GitHub repository inventory and hygiene report. Python stdlib only."""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"

def get(url, token):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "belentani-repo-health/1"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)

def inventory(owner, token, limit):
    repos = []
    page = 1
    while True:
        params = urllib.parse.urlencode({"per_page": 100, "page": page, "type": "owner"})
        url = f"{API}/users/{urllib.parse.quote(owner)}/repos?{params}"
        if token:
            url = f"{API}/user/repos?{urllib.parse.urlencode({'per_page':100,'page':page,'affiliation':'owner','sort':'full_name'})}"
        batch = get(url, token)
        if not isinstance(batch, list):
            raise ValueError("GitHub repositories response must be a list")
        # Pagination must use the raw API page size, not the owner-filtered
        # number; otherwise mixed-owner pages can end the scan too soon.
        selected = ([r for r in batch if r.get("owner", {}).get("login", "").lower() == owner.lower()]
                    if token else batch)
        repos.extend(selected)
        if len(batch) < 100 or (limit and len(repos) >= limit):
            break
        page += 1
    return repos[:limit] if limit else repos

def inspect(repo, token):
    owner, name = repo["full_name"].split("/", 1)
    base = f"{API}/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}"
    default = repo.get("default_branch") or "main"
    root = []
    try:
        root = get(base + "/contents?ref=" + urllib.parse.quote(default), token)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
        pass
    names = {item.get("name", "").lower() for item in root if isinstance(item, dict)}
    workflows = ".github" in names
    checks = {
        "readme": any(x.startswith("readme") for x in names),
        "license": any(x.startswith("license") or x.startswith("copying") for x in names),
        "gitignore": ".gitignore" in names,
        "contributing": any(x.startswith("contributing") for x in names),
        "security_policy_root": "security.md" in names,
        "github_directory": workflows,
        "tests_directory": any(x in names for x in ("tests", "test", "__tests__")),
    }
    score = sum(checks.values())
    return {
        "repository": repo["full_name"],
        "url": repo["html_url"],
        "private": repo.get("private", False),
        "archived": repo.get("archived", False),
        "language": repo.get("language") or "",
        "default_branch": default,
        "updated_at": repo.get("updated_at", ""),
        "open_issues": repo.get("open_issues_count", 0),
        "hygiene_score": score,
        "hygiene_max": len(checks),
        "checks": checks,
        "notes": ["Root-only heuristics; .github workflows and nested tests not verified.",
                  "No branch protection, secret scanning, or CI success claims."],
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", default="belentani7")
    p.add_argument("--out", default="github-health")
    p.add_argument("--limit", type=int, default=0, help="0 scans all accessible owned repos")
    args = p.parse_args()
    if args.limit < 0:
        p.error("--limit must be >= 0")
    token = os.environ.get("GITHUB_TOKEN", "")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        repos = inventory(args.owner, token, args.limit)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
        print(f"Inventory failed: {e}", file=sys.stderr)
        return 1
    results = []
    for repo in repos:
        try:
            results.append(inspect(repo, token))
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
            print(f"Skipped {repo.get('full_name')}: {e}", file=sys.stderr)
    stamp = datetime.now(timezone.utc).isoformat()
    (out / "inventory.json").write_text(json.dumps({"generated_at": stamp, "owner": args.owner, "repos": results}, indent=2), encoding="utf-8")
    with (out / "inventory.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["repository","url","private","archived","language","default_branch","updated_at","open_issues","hygiene_score","hygiene_max"])
        writer.writeheader()
        for result in results:
            writer.writerow({key: result[key] for key in writer.fieldnames})
    lines = [f"# GitHub hygiene snapshot — {args.owner}", "", f"Generated: {stamp}", f"Repositories inspected: {len(results)}", "", "Root-file presence is not proof of security or quality.", "", "| Repository | Root checks | Missing signals |", "|---|---:|---|"]
    for r in sorted(results, key=lambda x: (x["hygiene_score"], x["repository"])):
        missing = ", ".join(k for k, v in r["checks"].items() if not v) or "none"
        lines.append(f'| [{r["repository"]}]({r["url"]}) | {r["hygiene_score"]}/{r["hygiene_max"]} | {missing} |')
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Inspected {len(results)} repositories. Reports in {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
