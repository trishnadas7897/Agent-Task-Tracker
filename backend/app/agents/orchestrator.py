"""
MultiAgentOrchestrator.

Composes the three agents - AnalyzerAgent -> ExecutorAgent -> ValidatorAgent -
threading each agent's structured output into the next agent's context, and
persists per-agent traces to MongoDB so the activity log can show the entire
multi-agent run.

If the validator returns VERDICT: REVISE with a non-empty REVISION, that
revision replaces the executor's draft as the final answer. If any agent
errors fatally, the orchestrator short-circuits, marks the task `error`, and
records the partial trace.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pymongo.errors import PyMongoError

from app import mongo

from .analyzer import AnalyzerAgent
from .base import AgentRun
from .executor import ExecutorAgent
from .validator import ValidatorAgent, parse_validator_output


class MultiAgentOrchestrator:
    """
    Three-agent pipeline. Stateless - one instance can serve every request.
    """

    def __init__(self) -> None:
        self.analyzer = AnalyzerAgent()
        self.executor = ExecutorAgent()
        self.validator = ValidatorAgent()

    def run(self, task_id: str, user_id: str) -> Dict[str, Any]:
        task = mongo.db.tasks.find_one({"task_id": task_id, "user_id": user_id})
        if not task:
            raise ValueError("Task not found")

        context: Dict[str, Any] = {
            "task": task,
            "task_id": task_id,
            "user_id": user_id,
        }
        agent_runs: List[AgentRun] = []

        # ---- agent 1: ANALYZER ----
        analyzer_run = self.analyzer.run(context)
        agent_runs.append(analyzer_run)
        if analyzer_run.error:
            return self._fail(task_id, user_id, agent_runs, analyzer_run.error)
        context["analyzer_output"] = analyzer_run.output

        # ---- agent 2: EXECUTOR ----
        executor_run = self.executor.run(context)
        agent_runs.append(executor_run)
        if executor_run.error:
            return self._fail(task_id, user_id, agent_runs, executor_run.error)
        context["executor_output"] = executor_run.output

        # ---- agent 3: VALIDATOR ----
        validator_run = self.validator.run(context)
        agent_runs.append(validator_run)
        # A validator failure is non-fatal: we fall back to the executor draft,
        # because publishing a usable draft beats erroring on a guardrail miss.
        verdict, revision = parse_validator_output(validator_run.output)
        final_answer = revision if (verdict == "REVISE" and revision) else executor_run.output

        # ---- persist + log success ----
        return self._succeed(
            task_id=task_id,
            user_id=user_id,
            agent_runs=agent_runs,
            verdict=verdict,
            final_answer=final_answer,
        )

    # ---- DB helpers ----

    def _succeed(
        self,
        task_id: str,
        user_id: str,
        agent_runs: List[AgentRun],
        verdict: str,
        final_answer: str,
    ) -> Dict[str, Any]:
        trace = [r.to_dict() for r in agent_runs]
        now = datetime.utcnow()
        try:
            mongo.db.tasks.update_one(
                {"task_id": task_id, "user_id": user_id},
                {
                    "$set": {
                        "status": "completed",
                        "progress": 100,
                        "result": final_answer,
                        "validator_verdict": verdict,
                        "agent_trace": trace,
                        "last_run": now,
                    }
                },
            )
            mongo.db.logs.insert_one(
                {
                    "task_id": task_id,
                    "user_id": user_id,
                    "ai_response": final_answer,
                    "status": "success",
                    "agent_trace": trace,
                    "validator_verdict": verdict,
                    "timestamp": now,
                }
            )
        except PyMongoError as exc:
            print(f"[orchestrator] failed to persist success: {exc}")

        return {
            "task_id": task_id,
            "user_id": user_id,
            "results": final_answer,
            "validator_verdict": verdict,
            "agent_trace": trace,
            "steps_completed": [r.agent_name for r in agent_runs],
            "error": None,
        }

    def _fail(
        self,
        task_id: str,
        user_id: str,
        agent_runs: List[AgentRun],
        error: str,
    ) -> Dict[str, Any]:
        trace = [r.to_dict() for r in agent_runs]
        now = datetime.utcnow()
        try:
            mongo.db.tasks.update_one(
                {"task_id": task_id, "user_id": user_id},
                {
                    "$set": {
                        "status": "error",
                        "agent_trace": trace,
                        "last_run": now,
                    }
                },
            )
            mongo.db.logs.insert_one(
                {
                    "task_id": task_id,
                    "user_id": user_id,
                    "ai_response": f"Error: {error}",
                    "status": "error",
                    "agent_trace": trace,
                    "timestamp": now,
                }
            )
        except PyMongoError as exc:
            print(f"[orchestrator] failed to persist error: {exc}")

        return {
            "task_id": task_id,
            "user_id": user_id,
            "results": None,
            "agent_trace": trace,
            "steps_completed": [r.agent_name for r in agent_runs],
            "error": error,
        }


# Module-level shared instance + functional entry-point so callers do not
# need to know about the orchestrator class.
_orchestrator: Optional[MultiAgentOrchestrator] = None


def run_multi_agent_pipeline(task_id: str, user_id: str) -> Dict[str, Any]:
    """
    Run the three-agent pipeline for a task. This is the public API the
    Flask route hits via langchain_tools.run_agent_for_task (kept as a thin
    shim for backwards compatibility).
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    try:
        return _orchestrator.run(task_id, user_id)
    except Exception as exc:  # noqa: BLE001 - top-level guard
        return {
            "task_id": task_id,
            "user_id": user_id,
            "results": None,
            "agent_trace": [],
            "steps_completed": [],
            "error": str(exc),
        }
