import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Local dev only. Prod uses gunicorn (see render.yaml startCommand),
    # so this block never runs in production. Bind 0.0.0.0 + $PORT defensively
    # in case anything ever launches run.py directly on a host.
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
