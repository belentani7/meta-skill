"""Generate private, local inventory from GitHub CLI; never commit private metadata."""
import argparse
import json
import subprocess
from pathlib import Path

def collect(owner="belentani7"):
    cmd = ["gh", "repo", "list", owner, "--limit", "1000",
           "--json", "nameWithOwner,visibility,isArchived,defaultBranchRef"]
    data = json.loads(subprocess.check_output(cmd, text=True, timeout=60))
    return {"schema_version": 1, "repositories": [
        {"name": r["nameWithOwner"], "visibility": r["visibility"],
         "archived": r["isArchived"]} for r in data]}
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--owner", default="belentani7")
    args = p.parse_args()
    dest = Path(args.output).resolve()
    if dest.is_relative_to(Path(__file__).resolve().parents[1]):
        raise SystemExit("Inventory must be outside repository working tree")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(collect(args.owner), indent=2))
    dest.chmod(0o600)
if __name__ == "__main__":
    main()
