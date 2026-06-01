import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from app import mongo
from pymongo.errors import PyMongoError

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Default to 2.5-flash because the free tier no longer serves 1.5/2.0 flash models.
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
# Build the endpoint from the model name so they can never drift apart.
# Callers may still override with GEMINI_API_ENDPOINT for a different model/version.
GEMINI_API_ENDPOINT = os.getenv(
    "GEMINI_API_ENDPOINT",
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent",
)

def test_gemini_api():
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY,
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello, this is a test."}
                ]
            }
        ]
    }

    response = requests.post(GEMINI_API_ENDPOINT, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        try:
            print(data["candidates"][0]["content"])
        except (KeyError, IndexError):
            print("Unexpected Gemini API response structure:", data)
    else:
        print(f"Gemini API error {response.status_code}: {response.text}")

def get_gemini_response(prompt: str) -> str | None:
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY,
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        # 30s headroom: 2.5 Flash + Render free-tier cold start can both eat budget.
        response = requests.post(GEMINI_API_ENDPOINT, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            print(f"Gemini API error {response.status_code}: {response.text}")
            return None

        data = response.json()
        print("Gemini API full response:", data)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Exception during Gemini API call: {e}")
        return None

def run_agent_for_task(task_id: str, user_id: str) -> dict:
    """
    Agentic AI loop for a task:
    - Multi-step: analyze, call Gemini, post-process, finalize
    - Updates task status & logs in MongoDB
    Returns dict with results or error info.
    """
    context = {
        "task_id": task_id,
        "user_id": user_id,
        "results": None,
        "error": None,
        "steps_completed": [],
    }
    try:
        task = mongo.db.tasks.find_one({"task_id": task_id, "user_id": user_id})
        if not task:
            raise Exception("Task not found")

        # Define steps for the agent to execute
        steps = [
            "analyze_task",
            "call_gemini_api",
            "postprocess_response",
            "finalize_task",
        ]

        for step in steps:
            if step == "analyze_task":
                # You can add more complex analysis here if needed
                context["analysis"] = f"Analyzing task titled '{task.get('title', '')}'."
                context["steps_completed"].append(step)

            elif step == "call_gemini_api":
                prompt_template = (
                    "You are a professional support agent.\n"
                    "Task title: {title}\n"
                    "Description: {description}\n"
                    "Please provide a concise, professional response."
                )
                prompt = prompt_template.format(
                    title=task.get("title", ""),
                    description=task.get("description", "")
                )
                response = get_gemini_response(prompt)
                if not response:
                    raise Exception("Gemini API returned no response")
                context["results"] = response
                context["steps_completed"].append(step)

            elif step == "postprocess_response":
                if context["results"]:
                    context["results"] = context["results"].strip()
                context["steps_completed"].append(step)

            elif step == "finalize_task":
                mongo.db.tasks.update_one(
                    {"task_id": task_id, "user_id": user_id},
                    {"$set": {
                        "status": "completed",
                        "progress": 100,
                        "result": context["results"],
                        "last_run": datetime.utcnow(),
                    }}
                )
                mongo.db.logs.insert_one({
                    "task_id": task_id,
                    "user_id": user_id,
                    "ai_response": context["results"],
                    "status": "success",
                    "timestamp": datetime.utcnow(),
                })
                context["steps_completed"].append(step)

        return context

    except Exception as e:
        context["error"] = str(e)
        # Mark task as error and log it
        try:
            mongo.db.tasks.update_one(
                {"task_id": task_id, "user_id": user_id},
                {"$set": {"status": "error", "last_run": datetime.utcnow()}}
            )
            mongo.db.logs.insert_one({
                "task_id": task_id,
                "user_id": user_id,
                "ai_response": f"Error: {context['error']}",
                "status": "error",
                "timestamp": datetime.utcnow(),
            })
        except PyMongoError as log_error:
            print(f"Failed to log error in MongoDB: {log_error}")
        return context

if __name__ == "__main__":
    test_gemini_api()
