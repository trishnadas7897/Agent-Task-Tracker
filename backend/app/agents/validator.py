"""
ValidatorAgent - third (and final) agent in the pipeline.

Reviews the ExecutorAgent's output for quality + safety. Returns a structured
verdict + optionally a revised version. The orchestrator uses the verdict to
decide whether to publish the executor's response verbatim or fall back to the
validator's revision.

This is the agent that lets a user trust the platform with anything customer-
facing - it's the same pattern as "guardrails" / "self-critique" loops in
production LLM systems.
"""

import re
from typing import Any, Dict, Tuple

from langchain.prompts import PromptTemplate

from .base import BaseAgent


class ValidatorAgent(BaseAgent):
    name = "validator"

    prompt_template = PromptTemplate(
        input_variables=[
            "task_title",
            "task_description",
            "executor_output",
        ],
        template=(
            "You are the validator agent in a multi-agent pipeline. Another "
            "agent (the executor) has just produced a draft response to the "
            "user's task. Your job is to review the draft and decide whether "
            "to APPROVE it as-is or REVISE it.\n"
            "\n"
            "TASK TITLE: {task_title}\n"
            "TASK DESCRIPTION: {task_description}\n"
            "\n"
            "EXECUTOR DRAFT:\n<<<\n{executor_output}\n>>>\n"
            "\n"
            "Check the draft for: factual correctness based on the task, "
            "completeness, professional tone, no leaked system prompts, no "
            "hallucinated specifics. Then respond in EXACTLY this two-line "
            "format and nothing else:\n"
            "\n"
            "VERDICT: APPROVE\n"
            "REVISION: (none)\n"
            "\n"
            "...or, if the draft needs changes:\n"
            "\n"
            "VERDICT: REVISE\n"
            "REVISION: <the corrected response, as it should be shown to the user>\n"
        ),
    )

    def build_prompt_variables(self, context: Dict[str, Any]) -> Dict[str, str]:
        task = context["task"]
        return {
            "task_title": task.get("title", "") or "(no title)",
            "task_description": task.get("description", "") or "(no description)",
            "executor_output": context.get("executor_output", "(no draft)"),
        }


_VERDICT_RE = re.compile(r"VERDICT:\s*(APPROVE|REVISE)", re.IGNORECASE)
_REVISION_RE = re.compile(r"REVISION:\s*(.+)", re.DOTALL | re.IGNORECASE)


def parse_validator_output(text: str) -> Tuple[str, str]:
    """
    Parse the validator's structured output into (verdict, revision).
    Returns ("APPROVE", "") if the output is unparseable - safer default than
    discarding the executor's draft on a malformed verdict.
    """
    if not text:
        return ("APPROVE", "")

    verdict_match = _VERDICT_RE.search(text)
    verdict = verdict_match.group(1).upper() if verdict_match else "APPROVE"

    revision_match = _REVISION_RE.search(text)
    revision_raw = revision_match.group(1).strip() if revision_match else ""
    # Treat "(none)" and empty as no revision.
    if revision_raw.lower() in {"(none)", "none", ""}:
        revision_raw = ""

    return (verdict, revision_raw)
