"""
ExecutorAgent - second agent in the pipeline.

Takes the AnalyzerAgent's labelled output plus the original task and produces
the actual response a user would see. The agent's "persona" is dictated by
the task type so a Classification task gets a different system prompt than a
Translation task.
"""

from typing import Any, Dict

from langchain.prompts import PromptTemplate

from .base import BaseAgent


# Per-task-type persona, so the executor adapts its tone + format to the
# task. Adding a new task type is a one-line change.
EXECUTOR_PERSONAS: Dict[str, str] = {
    "Classification": (
        "a precise classification assistant. Return ONLY the resolved class "
        "label (or short ranked list) with a one-sentence justification."
    ),
    "Summarization": (
        "a professional summarization assistant. Return a concise summary "
        "(<= 5 bullet points or <= 120 words). No preamble."
    ),
    "Translation": (
        "an expert translator. Return ONLY the translated text in the target "
        "language, preserving meaning, register, and proper nouns."
    ),
    "Custom": (
        "a helpful, professional task-execution agent. Follow the user's "
        "instructions literally and respond directly."
    ),
}

DEFAULT_PERSONA = EXECUTOR_PERSONAS["Custom"]


class ExecutorAgent(BaseAgent):
    name = "executor"

    prompt_template = PromptTemplate(
        input_variables=[
            "persona",
            "task_type",
            "task_title",
            "task_description",
            "analyzer_output",
        ],
        template=(
            "You are {persona}\n"
            "\n"
            "You are the executor in a multi-agent pipeline. An analyzer agent "
            "has already inspected the user's task and produced the analysis "
            "between <analysis> tags below. Use it to shape your response, but "
            "your final output should be a polished answer to the original task, "
            "not a meta-discussion of the analysis.\n"
            "\n"
            "<analysis>\n{analyzer_output}\n</analysis>\n"
            "\n"
            "TASK TYPE: {task_type}\n"
            "TASK TITLE: {task_title}\n"
            "TASK DESCRIPTION: {task_description}\n"
            "\n"
            "Produce the final response now."
        ),
    )

    def build_prompt_variables(self, context: Dict[str, Any]) -> Dict[str, str]:
        task = context["task"]
        task_type = task.get("type", "General") or "General"
        return {
            "persona": EXECUTOR_PERSONAS.get(task_type, DEFAULT_PERSONA),
            "task_type": task_type,
            "task_title": task.get("title", "") or "(no title)",
            "task_description": task.get("description", "") or "(no description)",
            "analyzer_output": context.get("analyzer_output", "(no prior analysis)"),
        }
