from flask import Blueprint, request, jsonify, g
from app.utils.jwt_helper import token_required
from app import mongo

profile_bp = Blueprint("profile", __name__)

# ---------------- GET Profile ----------------
@profile_bp.route("/", methods=["GET"])
@token_required
def get_profile():
    user = mongo.db.users.find_one(
        {"user_id": g.user_id},
        {"_id": 0, "password": 0}
    )

    if not user:
        # If this fires after the login fix, there is a real bug. Do NOT mask
        # it by inserting a phantom user (the old behaviour caused duplicate
        # blank profiles on every fresh login).
        return jsonify({"error": "User not found"}), 404

    return jsonify(user), 200


# ---------------- UPDATE Profile ----------------
@profile_bp.route("/", methods=["PUT"])
@token_required
def update_profile():
    data = request.get_json()

    # Fields allowed to update
    allowed_fields = [
        "firstName", "lastName", "email", "phone",
        "location", "role", "department", "timezone"
    ]

    update_data = {field: data[field] for field in allowed_fields if field in data}

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    result = mongo.db.users.update_one(
        {"user_id": g.user_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"message": "Profile updated successfully"}), 200
