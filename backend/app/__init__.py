from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
from flask_restx import Api
from flask_cors import CORS

mongo = PyMongo()

api = Api(title="KPI Agent API", version="1.0", doc="/docs")  # <- enables Swagger at /docs


def create_app():
    load_dotenv()  # Load env variables
    app = Flask(__name__)

    # CORS: env-driven allowlist. Bearer-token auth (no cookies) -> credentials off.
    # Set CORS_ORIGINS as a comma-separated list of exact origins (no trailing slash).
    origins = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        supports_credentials=False,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )

    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    app.config["JWT_SECRET"] = os.getenv("JWT_SECRET")
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    app.config["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
    mongo.init_app(app)

    api.init_app(app)
    # Import and register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.task_routes import task_bp
    from app.routes.ai_routes import ai_bp
    from app.routes.logs_routes import logs_bp
    from app.routes.profile_routes import profile_bp
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(auth_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(logs_bp)

    # Unauthenticated liveness probe for Render health checks + keep-warm cron.
    # Intentionally does NOT touch Mongo or Gemini so it stays cheap and reliable.
    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
