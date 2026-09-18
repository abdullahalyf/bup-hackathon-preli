"""OpenAI-compatible JSON-mode client with primary + fallback providers.

Owner: Tamjid. Loaded by app.interpreter.core. Never logs or prints API keys.

Contract (docs/CONTRACTS.md §Internal Python contracts):
  call_llm(system: str, user: str) -> dict

The function returns a parsed dict on success. On any failure (timeout,
HTTP 4xx/5xx, JSON parse error, schema mismatch) it raises LLMClientError.
The caller (core.py) decides whether to retry, fall back, or no-op.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

log = logging.getLogger(__name__)

# Per-attempt timeout. Brief says <3 s p50; we cap each call at 8 s and
# fall back on any miss. The pipeline as a whole stays well under budget.
_REQUEST_TIMEOUT_S = 8.0


class LLMClientError(Exception):
    """Raised when neither primary nor fallback provider returns usable JSON."""


class Provider:
    """A single OpenAI-compatible endpoint + key + model."""

    def __init__(self, label: str, api_key, base_url, model):
        self.label = label
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip() or None
        self.model = (model or "").strip() or None

    @property
    def usable(self):
        return bool(self.api_key and self.model)

    def _build_client(self):
        kwargs = {"api_key": self.api_key, "timeout": _REQUEST_TIMEOUT_S}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def _extra_body(self):
        """Provider-specific knobs. Empty by default; kept for future use."""
        return {}

    def call(self, system, user):
        """One JSON-mode call. Returns parsed dict. Raises LLMClientError on failure."""
        if not self.usable:
            raise LLMClientError("provider '" + self.label + "' not configured")

        client = self._build_client()
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "max_tokens": 1024,
        }
        extra = self._extra_body()
        if extra:
            kwargs["extra_body"] = extra

        try:
            t0 = time.time()
            resp = client.chat.completions.create(**kwargs)
            elapsed = time.time() - t0
            content = (resp.choices[0].message.content or "").strip()
            log.info("%s OK in %.2fs", self.label, elapsed)
        except (APITimeoutError, APIConnectionError) as exc:
            raise LLMClientError(self.label + " network/timeout") from exc
        except RateLimitError as exc:
            raise LLMClientError(self.label + " rate-limited") from exc
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise LLMClientError(self.label + " auth denied") from exc
        except (BadRequestError, NotFoundError) as exc:
            raise LLMClientError(self.label + " bad request / not found") from exc
        except Exception as exc:
            raise LLMClientError(self.label + " unexpected: " + exc.__class__.__name__) from exc

        if not content:
            raise LLMClientError(self.label + " empty response")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMClientError(self.label + " non-JSON content") from exc
        if not isinstance(parsed, dict):
            raise LLMClientError(self.label + " JSON is not an object")
        return parsed


def _build_providers():
    primary = Provider(
        label="primary",
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL"),
        model=os.getenv("LLM_MODEL"),
    )
    fallback = Provider(
        label="fallback",
        api_key=os.getenv("LLM_FALLBACK_API_KEY") or os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_FALLBACK_BASE_URL") or os.getenv("LLM_BASE_URL"),
        model=os.getenv("LLM_FALLBACK_MODEL") or os.getenv("LLM_MODEL"),
    )
    return [primary, fallback]


def call_llm(system, user):
    """Try primary, then fallback. Return dict. Raise LLMClientError if both fail."""
    last_err = None
    for provider in _build_providers():
        if not provider.usable:
            continue
        try:
            return provider.call(system, user)
        except LLMClientError as exc:
            log.warning("%s failed: %s", provider.label, exc)
            last_err = exc
    raise LLMClientError(str(last_err) if last_err else "no provider configured")


if __name__ == "__main__":
    import sys

    # The test runner expects .env to be picked up. We import here to avoid
    # forcing dotenv at module import time (the real app does it in main.py).
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_system = "Return strictly valid JSON only, no commentary. Schema: {\"ok\": bool, \"echo\": string}"
    test_user = "Set ok=true and echo this prompt back."
    try:
        t0 = time.time()
        out = call_llm(test_system, test_user)
        dt = time.time() - t0
        print(json.dumps({"latency_s": round(dt, 3), "response": out}))
        sys.exit(0)
    except LLMClientError as exc:
        print(json.dumps({"error": str(exc)}))
        sys.exit(1)
