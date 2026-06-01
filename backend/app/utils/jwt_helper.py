import jwt
import datetime
from flask import current_app, request, jsonify, g
from functools import wraps

__all__ = ["generate_jwt_token", "token_required"]


# 🔐 Generate JWT Token
def generate_jwt_token(user_id: str) -> str:
    """
    Generate a JWT for an authenticated user.

    CONTRACT: `user_id` MUST be the canonical UUID stored on the user document
    (the `user_id` field), NOT the Mongo `_id` ObjectId. Every downstream query
    in this app filters by {"user_id": <uuid>}; signing with `_id` will cause
    silent empty-result bugs in tasks/logs/profile.

    Expiration defaults to 1 day (configurable via JWT_EXP_DAYS in app config).
    """
    if not isinstance(user_id, str) or len(user_id) != 36 or user_id.count("-") != 4:
        raise ValueError(
            "generate_jwt_token expects a UUID4 string (user_id), not a Mongo ObjectId"
        )

    expiry_days = current_app.config.get("JWT_EXP_DAYS", 1)
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=expiry_days),
        "iat": datetime.datetime.utcnow()
    }

    secret = current_app.config.get("JWT_SECRET", "default_secret_key")
    print(f"🔐 [generate_jwt_token] Using JWT_SECRET: {secret}")

    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


# 🔒 Token Verification Decorator
def token_required(f):
    """
    Decorator to protect routes with JWT authentication.
    Requires 'Authorization: Bearer <token>' in the request headers.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = current_app.config.get("JWT_SECRET", "default_secret_key")

        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header or not auth_header.startswith("Bearer "):
            print("❌ Missing or malformed Authorization header")
            return jsonify({"error": "Authorization header must start with 'Bearer'"}), 401

        token = auth_header.split("Bearer ")[1].strip()

        try:
            print(f"🔑 [token_required] Using JWT_SECRET: {secret}")
            print(f"🪪 Received Token: {token}")

            decoded = jwt.decode(token, secret, algorithms=["HS256"])
            print(f"✅ Token Decoded: {decoded}")

            # Save user_id for use in routes
            g.user_id = decoded.get("user_id")

        except jwt.ExpiredSignatureError:
            print("❌ Token has expired")
            return jsonify({"error": "Token has expired"}), 401

        except jwt.InvalidTokenError as e:
            print(f"❌ Invalid token: {str(e)}")
            return jsonify({"error": "Invalid token"}), 401

        except Exception as e:
            print(f"❌ Unexpected error during token verification: {str(e)}")
            return jsonify({"error": f"Token verification failed: {str(e)}"}), 401

        return f(*args, **kwargs)
    return decorated
