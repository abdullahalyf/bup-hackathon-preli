"""OpenAI-compatible LLM client for directive interpretation.

Primary and fallback providers are configured via env vars. Both expose the
OpenAI chat-completions interface and the `/models` list endpoint.

Env (names only; values are never logged):
  LLM_API_KEY, LLM_BASE_URL, LLM_MODEL            (primary)
  LLM_FALLBACK_API_KEY, LLM_FALLBACK_BASE_URL,
  LLM_FALLBACK_MODEL                              (fallback)

Behaviour:
  * call_llm_json(system, user) -> dict (parsed JSON) or {}
  * temperature 0, response_format json_object, hard timeout 8s
  * primary failure / 429 / timeout -> single fallback attempt
  * on any failure returns {} (caller treats as "retry / fallback")
  * never logs keys, never prints raw provider responses
"""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:  # load .env so the module works when imported outside app.main
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


TIMEOUT_S = 8.0


def _provider_config(role: str) -> tuple[str, str, str] | None:
    if role == "fallback":
        base = os.getenv("LLM_FALLBACK_BASE_URL")
        key = os.getenv("LLM_FALLBACK_API_KEY")
        model = os.getenv("LLM_FALLBACK_MODEL")
    else:
        base = os.getenv("LLM_BASE_URL")
        key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL")
    if not (base and key and model):
        return None
    return base.rstrip("/"), key, model


def list_models(base_url: str, api_key: str, timeout: float = 6.0) -> list[str]:
    req = Request(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    names: list[str] = []
    for item in data.get("data", []):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            names.append(item["id"])
    return names


def _is_transient_failure(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, (URLError, TimeoutError, OSError))


def _chat_once(base_url: str, api_key: str, model: str, system: str,
               user: str, timeout: float) -> dict[str, Any]:
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = Request(
        f"{base_url}/chat/completions",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(content, str):
        return {}
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def call_llm_json(system: str, user: str, timeout: float = TIMEOUT_S) -> dict[str, Any]:
    last_exc: Exception | None = None
    for role in ("primary", "fallback"):
        cfg = _provider_config(role)
        if cfg is None:
            continue
        base, key, model = cfg
        try:
            result = _chat_once(base, key, model, system, user, timeout)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if _is_transient_failure(exc):
                continue
            return {}
        if result:
            return result
    return {}


def model_status() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for role in ("primary", "fallback"):
        cfg = _provider_config(role)
        if cfg is None:
            out[role] = {"configured": False}
            continue
        base, key, model = cfg
        available = list_models(base, key, timeout=4.0)
        out[role] = {
            "configured": True,
            "base_url": base,
            "model": model,
            "model_listed": (model in available) if available else "unknown",
        }
    return out


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(model_status(), indent=2))
    out = call_llm_json(
        "Reply only with JSON.",
        'JSON: {"hello": "world"}',
    )
    print(json.dumps(out))
