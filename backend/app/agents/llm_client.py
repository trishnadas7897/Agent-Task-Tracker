"""
Provider-agnostic LLM client. Both supported providers have a $0 free tier:

  LLM_PROVIDER=gemini  -> Google AI Studio free tier (gemini-2.5-flash)
                          1,500 req/day, 15 req/min, no card.
  LLM_PROVIDER=groq    -> Groq free tier (llama-3.3-70b-versatile)
                          ~1,000 req/day/model, sub-200ms, no training.

Swap providers with one env var; no code change. call_gemini() is kept as a
backwards-compat alias so existing agent imports keep working.
"""
import os
import time
from typing import Optional

import requests

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
DEFAULT_TIMEOUT_S = 30
MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))  # retry transient 429/503

# ---- Gemini (free tier) ----
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
GEMINI_ENDPOINT = os.getenv(
    "GEMINI_API_ENDPOINT",
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent",
)

# ---- Groq (free tier, OpenAI-compatible) ----
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(RuntimeError):
    pass


def _call_gemini(prompt: str, timeout: int) -> str:
    if not GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY is not set")
    headers = {"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    r = requests.post(GEMINI_ENDPOINT, headers=headers, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise LLMError(f"Gemini {r.status_code}: {r.text[:300]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_groq(prompt: str, timeout: int) -> str:
    if not GROQ_API_KEY:
        raise LLMError("GROQ_API_KEY is not set")
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL_NAME, "messages": [{"role": "user", "content": prompt}]}
    r = requests.post(GROQ_ENDPOINT, headers=headers, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise LLMError(f"Groq {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"].strip()


_PROVIDERS = {"gemini": _call_gemini, "groq": _call_groq}


def call_llm(prompt: str, timeout: int = DEFAULT_TIMEOUT_S) -> str:
    fn = _PROVIDERS.get(LLM_PROVIDER)
    if fn is None:
        raise LLMError(f"Unknown LLM_PROVIDER={LLM_PROVIDER!r}; use 'gemini' or 'groq'")
    last: Optional[Exception] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return fn(prompt, timeout)
        except LLMError as exc:
            last = exc
            # Retry only on transient capacity/rate signals.
            if any(code in str(exc) for code in ("429", "503", "UNAVAILABLE")):
                time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
                continue
            raise
    raise last  # exhausted retries


def call_gemini(prompt: str, timeout: int = DEFAULT_TIMEOUT_S) -> str:
    """Backwards-compat alias used by existing agent code."""
    return call_llm(prompt, timeout)
