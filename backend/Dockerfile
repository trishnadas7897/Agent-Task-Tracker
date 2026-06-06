# --------------------------------------------------------------------------
# Agent Task Tracker - backend (Flask + gunicorn)
# Mirrors the Render production setup: gunicorn 1 worker / 4 threads, 120s
# timeout, binds 0.0.0.0:$PORT. Multi-stage to keep the runtime image lean.
# --------------------------------------------------------------------------

# ---------- stage 1: builder ----------
FROM python:3.12.7-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install deps into a separate prefix so we can copy just what we need into
# the runtime image.
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

# ---------- stage 2: runtime ----------
FROM python:3.12.7-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Non-root user so the container does not run as root in production.
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Bring in the pre-built site-packages from the builder stage.
COPY --from=builder /install /usr/local

# App source.
COPY --chown=app:app . .

USER app

EXPOSE 5000

# Healthcheck hits the unauthenticated /health endpoint added in 3326c86.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3).status == 200 else 1)"

# Same shape as render.yaml's startCommand so dev and prod behave the same.
CMD ["sh", "-c", "gunicorn run:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:${PORT}"]
