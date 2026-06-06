"""
AnalyzerAgent - first agent in the pipeline.

Reads the raw task (title + description) and produces a short structured
analysis: detected intent, key entities, suggested approach. The ExecutorAgent
uses this as additional context when drafting the actual response.

Why this matters: without an analyzer, a single-prompt agent has to "do the
right thing" purely from the user's task description. Splitting analysis from
execution gives the executor cleaner inputs and gives the activity log a
visible trail of "here is what the system thought you were asking".
"""

from typing import Any, Dict

from langchain.prompts import PromptTemplate

from .base import BaseAgent


class AnalyzerAgent(BaseAgent):
    name = "analyzer"

    prompt_template = PromptTemplate(
        input_variables=["task_title", "task_description", "task_type"],
        template=(
            "You are an analysis agent in a multi-agent task-processing pipeline.\n"
            "Your job is NOT to answer the user's request - only to analyze it.\n"
            "\n"
            "TASK TYPE: {task_type}\n"
            "TASK TITLE: {task_title}\n"
            "TASK DESCRIPTION: {task_description}\n"
            "\n"
            "Produce a concise analysis with exactly these three labelled lines:\n"
            "INTENT: <one short sentence: what does the user actually want?>\n"
            "ENTITIES: <comma-separated key entities / topics / inputs>\n"
            "APPROACH: <one short sentence: how should the executor agent respond?>\n"
            "\n"
            "Keep the whole analysis under 80 words. Do not include greetings, "
            "explanations, or any text outside the three labelled lines."
        ),
    )

    def build_prompt_variables(self, context: Dict[str, Any]) -> Dict[str, str]:
        task = context["task"]
        return {
            "task_title": task.get("title", "") or "(no title)",
            "task_description": task.get("description", "") or "(no description)",
            "task_type": task.get("type", "General") or "General",
        }
