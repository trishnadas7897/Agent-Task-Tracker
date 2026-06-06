"""
Gemini HTTP client, isolated so every agent shares the same retry / timeout
semantics and so we have a single place to swap in `google-generativeai` SDK
calls later.
"""

import os
from typing import Optional

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Default to 2.5-flash because the free tier no longer serves 1.5/2.0 flash.
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
# Build the endpoint from the model name so they can never drift apart.
GEMINI_API_ENDPOINT = os.getenv(
    "GEMINI_API_ENDPOINT",
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent",
)

# 30s headroom: 2.5 Flash + Render free-tier cold start can both eat budget.
DEFAULT_TIMEOUT_S = 30


class GeminiError(RuntimeError):
    """Raised when Gemini returns a non-200 or an unparseable response."""


def call_gemini(prompt: str, timeout: int = DEFAULT_TIMEOUT_S) -> str:
    """
    Send a single prompt to Gemini and return the text of the first candidate.

    Raises GeminiError on any HTTP or shape failure - callers (orchestrator
    or individual agents) decide whether to retry or mark the task errored.
    """
    if not GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY is not set")

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY,
    }
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(
            GEMINI_API_ENDPOINT, headers=headers, json=payload, timeout=timeout
        )
    except requests.RequestException as exc:
        raise GeminiError(f"Gemini request failed: {exc}") from exc

    if response.status_code != 200:
        raise GeminiError(
            f"Gemini API error {response.status_code}: {response.text[:500]}"
        )

    try:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise GeminiError(f"Unexpected Gemini response shape: {exc}") from exc


def safe_call_gemini(prompt: str, timeout: int = DEFAULT_TIMEOUT_S) -> Optional[str]:
    """
    Convenience wrapper returning None on error instead of raising. Use this
    only when the caller has a reasonable fallback for missing output.
    """
    try:
        return call_gemini(prompt, timeout=timeout)
    except GeminiError as exc:
        print(f"[gemini] {exc}")
        return None
