"""Quota-aware provider selector. Never rotates identities to evade limits."""
import json
import time
from pathlib import Path

class FreeApiMesh:
    def __init__(self, providers, clock=None):
        self.providers = providers
        self.clock = clock or time.time
        self.usage = {}
    def select(self, task, tokens=1):
        now = self.clock()
        eligible = []
        for p in self.providers:
            if task not in p.get("capabilities", []):
                continue
            if p.get("enabled") is not True:
                continue
            limit = p.get("daily_token_limit")
            if not isinstance(limit, int) or limit < 0:
                continue
            name = p["name"]
            day = int(now // 86400)
            used = self.usage.get((name, day), 0)
            if used + tokens <= limit:
                eligible.append(p)
        eligible.sort(key=lambda p: (-p.get("priority", 0), p["name"]))
        return eligible[0]["name"] if eligible else None
    def reserve(self, name, tokens):
        if not isinstance(tokens, int) or tokens <= 0:
            raise ValueError("Invalid token reservation")
        provider = next((p for p in self.providers if p["name"] == name), None)
        if provider is None or self.select_for_provider(provider, tokens) is False:
            return False
        key = (name, int(self.clock() // 86400))
        self.usage[key] = self.usage.get(key, 0) + tokens
        return True
    def select_for_provider(self, provider, tokens):
        if provider.get("enabled") is not True or not isinstance(provider.get("daily_token_limit"), int):
            return False
        key = (provider["name"], int(self.clock() // 86400))
        return self.usage.get(key, 0) + tokens <= provider["daily_token_limit"]
    def snapshot(self, path):
        data = [{"provider": name, "day": day, "tokens": count} for (name, day), count in self.usage.items()]
        Path(path).write_text(json.dumps(data, indent=2))
    def restore(self, path):
        for row in json.loads(Path(path).read_text()):
            self.usage[(row["provider"], row["day"])] = row["tokens"]
