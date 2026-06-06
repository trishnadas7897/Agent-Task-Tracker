"""
Backwards-compatibility shim.

Historically `ai_routes.py` called `run_agent_for_task` from this module, when
the pipeline was a single deterministic loop. The real implementation has now
moved to the multi-agent orchestrator at app/agents/orchestrator.py; this
module re-exports the public entry point so existing call sites and any
external scripts keep working without churn.

New code should import from `app.agents` directly:

    from app.agents import run_multi_agent_pipeline
"""

from dotenv import load_dotenv

from app.agents.gemini_client import GEMINI_API_ENDPOINT, GEMINI_API_KEY, call_gemini
from app.agents.orchestrator import run_multi_agent_pipeline

load_dotenv()


def run_agent_for_task(task_id: str, user_id: str) -> dict:
    """
    Three-agent pipeline (Analyzer -> Executor -> Validator) for a stored task.

    Kept as a free function so the existing Flask route in ai_routes.py does
    not need to be updated. Delegates 1:1 to the multi-agent orchestrator.
    """
    return run_multi_agent_pipeline(task_id, user_id)


# Re-exports for any caller that used to import these from here.
__all__ = [
    "run_agent_for_task",
    "run_multi_agent_pipeline",
    "call_gemini",
    "GEMINI_API_ENDPOINT",
    "GEMINI_API_KEY",
]
