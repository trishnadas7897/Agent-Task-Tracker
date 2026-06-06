"""
Multi-agent task-processing pipeline.

Three distinct agents, each with its own role, prompt, and Gemini call:

    AnalyzerAgent  ->  parses task intent + extracts entities/context
    ExecutorAgent  ->  produces the actual response using analyzer's output
    ValidatorAgent ->  reviews the executor's response, flags issues, can revise

Composed by MultiAgentOrchestrator (see orchestrator.py), which threads each
agent's output into the next agent's input, persists per-agent traces to
MongoDB, and returns the final validated response.

This replaces the earlier deterministic 4-step loop. Each agent is a real
LangChain Runnable with its own PromptTemplate, so adding a fourth agent
(e.g. SafetyReviewer, Summarizer, Router) is a one-class change.
"""

from .base import AgentRun, BaseAgent
from .analyzer import AnalyzerAgent
from .executor import ExecutorAgent
from .validator import ValidatorAgent
from .orchestrator import MultiAgentOrchestrator, run_multi_agent_pipeline

__all__ = [
    "AgentRun",
    "BaseAgent",
    "AnalyzerAgent",
    "ExecutorAgent",
    "ValidatorAgent",
    "MultiAgentOrchestrator",
    "run_multi_agent_pipeline",
]
