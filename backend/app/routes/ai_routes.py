from flask import Blueprint, jsonify, g
from app.utils.jwt_helper import token_required
from app.models.task_model import get_task_by_id
from app.utils.langchain_tools import run_agent_for_task
from app import mongo
from datetime import datetime

ai_bp = Blueprint("ai", __name__)

@ai_bp.route("/tasks/<task_id>/run-ai", methods=["POST"])
@token_required
def run_ai_for_task_route(task_id):
    """
    Run Gemini AI agent for a given stored task.
    Updates task status and logs the AI output.
    Returns the AI output as JSON.
    """
    try:
        user_id = g.user_id

        # Ensure task exists
        task = get_task_by_id(task_id, user_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404

        # Set task status to running
        mongo.db.tasks.update_one(
            {"task_id": task_id, "user_id": user_id},
            {"$set": {"status": "running", "last_run": datetime.utcnow()}}
        )

        # Run the agentic AI loop
        context = run_agent_for_task(task_id, user_id)

        if context.get("error"):
            # Mark task as error in DB if error occurred
            mongo.db.tasks.update_one(
                {"task_id": task_id, "user_id": user_id},
                {"$set": {"status": "error"}}
            )
            return jsonify({
                "error": "AI processing failed",
                "details": context["error"]
            }), 500

        # Debug print for backend logs
        print(f"Agentic AI completed for task {task_id} by user {user_id}. Steps completed: {context.get('steps_completed')}")
        
        # Return the AI response and metadata as JSON. The orchestrator now
        # threads three agents (analyzer/executor/validator) and persists their
        # trace + validator verdict; surface them so the UI and tests can see
        # which agents ran and how the validator scored the draft.
        return jsonify({
            "message": "Agentic AI task completed",
            "ai_response": context.get("results"),
            "steps_completed": context.get("steps_completed"),
            "validator_verdict": context.get("validator_verdict"),
            "agent_trace": context.get("agent_trace"),
        }), 200

    except Exception as e:
        # On unexpected failure, mark task as error
        mongo.db.tasks.update_one(
            {"task_id": task_id, "user_id": g.user_id},
            {"$set": {"status": "error"}}
        )
        print(f"Error in run_ai_for_task_route: {e}")
        return jsonify({
            "error": "AI processing failed",
            "details": str(e)
        }), 500
