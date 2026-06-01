from flask import Blueprint, request, jsonify
from app.models.user_model import get_user_by_email, create_user
from app.utils.jwt_helper import generate_jwt_token
import bcrypt
import uuid

auth_bp = Blueprint("auth", __name__)

# -------------------- Signup Route --------------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    if not all([email, password, name]):
        return jsonify({"error": "Missing fields"}), 400

    existing_user = get_user_by_email(email)
    if existing_user:
        return jsonify({"error": "User already exists"}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    user_id = str(uuid.uuid4())

    create_user(user_id=user_id, email=email, hashed_pw=hashed_pw, name=name)

    token = generate_jwt_token(user_id)

    return jsonify({
        "message": "User registered successfully",
        "token": token,
        "user_id": user_id,
        "name": name
    }), 201

# -------------------- Login Route --------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = get_user_by_email(email)
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    # Always sign with the canonical UUID stored on the user doc.
    # `_id` is a Mongo internal detail and must never leak into JWT claims,
    # otherwise downstream queries filtering by {"user_id": <uuid>} will all miss.
    if "user_id" not in user:
        return jsonify({"error": "Account is malformed, contact support"}), 500

    token = generate_jwt_token(user["user_id"])

    return jsonify({
        "token": token,
        "user_id": user["user_id"],
        "name": user["name"]
    }), 200
    