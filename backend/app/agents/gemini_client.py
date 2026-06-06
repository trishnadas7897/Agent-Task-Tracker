"""Back-compat shim. Real implementation lives in llm_client.py (provider-agnostic)."""
from .llm_client import (
    LLMError as GeminiError,        # old name kept as alias
    call_llm,
    call_gemini,
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    GEMINI_ENDPOINT as GEMINI_API_ENDPOINT,
)

__all__ = [
    "GeminiError",
    "call_llm",
    "call_gemini",
    "GEMINI_API_KEY",
    "GEMINI_MODEL_NAME",
    "GEMINI_API_ENDPOINT",
]
