"""Single policy-gated entrypoint for proposed operations; no tool side effects."""
import json
from pathlib import Path
try:
    from .guard import evaluate
except ImportError:
    from guard import evaluate

def preflight(action, inventory_path):
    inventory = json.loads(Path(inventory_path).read_text())
    names = [r["name"] for r in inventory["repositories"] if not r.get("archived")]
    return evaluate(action, names)

def prepare(action, inventory_path):
    decision = preflight(action, inventory_path)
    if not decision["allowed"]:
        raise PermissionError(json.dumps(decision["failures"]))
    return {"status": "authorized_for_external_executor", "action": action}
