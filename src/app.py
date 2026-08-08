"""FastAPI application for the Recruitment Assistant MVP.

Single-service delivery (SAD section 4): this one process serves both the JSON
API and the static single-page UI, so there is no separate frontend host and no
CORS surface for the MVP.

Endpoints:
- POST /api/recommend  -> runs the CrewAI crew and returns the ranked shortlist.
- GET  /health         -> {"status": "ok"} (boots without an API key).
- GET  /               -> serves src/static/index.html.

The app boots even when OPENAI_API_KEY is missing; the missing-key case is
surfaced as a clear error envelope from POST /api/recommend, not a crash.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Load environment variables from .env before importing runtime code that reads them.
load_dotenv()

# Support running both as "src.app" (package) and "app" (cwd=src).
try:
    from src.crew import RecommendationError, run_recommendation
except ImportError:  # pragma: no cover - fallback for cwd=src execution
    from crew import RecommendationError, run_recommendation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recruitment_assistant")

_SRC_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _SRC_DIR / "static"
_INDEX_FILE = _STATIC_DIR / "index.html"

app = FastAPI(title="Recruitment Assistant", version="0.1.0")


class RecommendRequest(BaseModel):
    """Request body for POST /api/recommend (SAD section 4)."""

    job_requirements: Any = Field(..., description="Role, key skills, and criteria. Required.")
    criteria: Optional[list] = Field(default=None, description="Optional list of criteria.")
    top_n: int = Field(default=5, ge=1, le=25, description="Max candidates in the shortlist.")


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    """Build the fixed error envelope: {"error": {"code", "message"}}."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


# HTTP status mapping for known RecommendationError codes.
_STATUS_BY_CODE = {
    "invalid_input": 400,
    "missing_api_key": 503,
    "runtime_unavailable": 503,
    "dataset_missing": 500,
    "dataset_invalid": 500,
    "dataset_empty": 500,
    "config_missing": 500,
    "config_invalid": 500,
    "output_unparseable": 502,
    "runtime_error": 502,
}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Works without an API key."""
    return {"status": "ok"}


@app.post("/api/recommend")
def recommend(request: RecommendRequest) -> JSONResponse:
    """Run the recommendation crew and return the ranked shortlist.

    On failure, returns the {"error": {"code", "message"}} envelope with an
    appropriate HTTP status and NO partial shortlist (PRD section 5).
    """
    try:
        result = run_recommendation(
            job_requirements=request.job_requirements,
            criteria=request.criteria,
            top_n=request.top_n,
        )
    except RecommendationError as exc:
        status_code = _STATUS_BY_CODE.get(exc.code, 500)
        logger.warning("recommend failed: code=%s message=%s", exc.code, exc.message)
        return _error_response(exc.code, exc.message, status_code)
    except Exception as exc:  # noqa: BLE001 - never leak a stack trace to the client
        logger.exception("unexpected error in recommend")
        return _error_response(
            "internal_error",
            f"An unexpected error occurred: {exc}",
            500,
        )

    logger.info("recommend ok: run_id=%s size=%d", result.get("run_id"), len(result.get("shortlist", [])))
    return JSONResponse(status_code=200, content=result)


@app.get("/")
def index() -> FileResponse:
    """Serve the single-page UI."""
    return FileResponse(str(_INDEX_FILE))


# Mount static assets last so the explicit routes above take precedence.
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
