"""Explicit provider adapters. No hidden retries or credential harvesting."""
import json
import os
import urllib.request

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "cerebras": ("https://api.cerebras.ai/v1/chat/completions", "CEREBRAS_API_KEY"),
    "sambanova": ("https://api.sambanova.ai/v1/chat/completions", "SAMBANOVA_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "ollama": ("http://127.0.0.1:11434/v1/chat/completions", None),
}
def completion(provider, model, messages, *, timeout=30, endpoint=None):
    if provider not in PROVIDERS:
        raise ValueError("Unknown provider")
    url, env = PROVIDERS[provider]
    if endpoint is not None:
        raise ValueError("Endpoint overrides prohibited")
    token = os.environ.get(env) if env else None
    if env and not token:
        raise RuntimeError("Missing provider credential")
    if not model or not isinstance(messages, list):
        raise ValueError("Invalid request")
    body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)
