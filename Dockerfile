# Recruitment Assistant MVP - single-service image (FastAPI + Uvicorn).
# Runtime target: crewai (AAMAD_TARGET_RUNTIME=crewai).
#
# Secrets are NEVER baked into this image. Provide them at run time with
# `--env-file .env` (docker run) or `env_file: .env` (docker compose).

FROM python:3.12-slim

# Keep Python output unbuffered and skip .pyc files for smaller, log-friendly runs.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so the layer caches when only app code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and runtime assets.
# Only what the service needs at run time (see .dockerignore for exclusions).
COPY main.py ./
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Document the service port. The container binds 0.0.0.0 internally so the
# published port is reachable; docker-compose publishes it on host loopback
# only (127.0.0.1) to preserve the security.md H1 mitigation.
EXPOSE 8000

# Run Uvicorn directly (no reload in the image). Host 0.0.0.0 is required for
# the container port to be reachable from the host; restrict exposure at the
# publish/host layer, not here.
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
