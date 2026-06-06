"""
BaseAgent + AgentRun.

Every agent in the pipeline inherits BaseAgent and returns an AgentRun.
AgentRun is what gets persisted to MongoDB so the activity log can show
the full multi-agent trace (which agent fired, what it produced, how
confident it was, how long it took).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from langchain.prompts import PromptTemplate

from .gemini_client import GeminiError, call_gemini


@dataclass
class AgentRun:
    """The result of one agent invocation. Serializable to MongoDB."""

    agent_name: str
    output: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["started_at"] = self.started_at.isoformat()
        d["finished_at"] = self.finished_at.isoformat()
        return d


class BaseAgent(ABC):
    """
    Contract every agent must satisfy.

    Subclasses set `name` and `prompt_template` (a LangChain PromptTemplate)
    and implement `build_prompt_variables(context)`. The base `run` handles
    timing, Gemini invocation, and AgentRun packaging - so every agent has
    the same operational shape.
    """

    name: str = "base"
    prompt_template: PromptTemplate

    @abstractmethod
    def build_prompt_variables(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Map the orchestrator's running context to the variables this agent's
        PromptTemplate needs. Each agent owns its own contract here.
        """

    def run(self, context: Dict[str, Any]) -> AgentRun:
        """
        Execute one Gemini round-trip for this agent. The orchestrator calls
        this and threads the AgentRun back into its context for the next
        agent.
        """
        started = datetime.utcnow()
        try:
            variables = self.build_prompt_variables(context)
            prompt = self.prompt_template.format(**variables)
            output = call_gemini(prompt)
            error: Optional[str] = None
        except GeminiError as exc:
            output = ""
            error = str(exc)
        except KeyError as exc:
            # PromptTemplate complained about a missing variable - fatal but
            # caught so the orchestrator can mark the task errored cleanly.
            output = ""
            error = f"Missing prompt variable: {exc}"

        finished = datetime.utcnow()
        return AgentRun(
            agent_name=self.name,
            output=output,
            started_at=started,
            finished_at=finished,
            duration_ms=int((finished - started).total_seconds() * 1000),
            metadata={"prompt_template": self.prompt_template.template[:200]},
            error=error,
        )
