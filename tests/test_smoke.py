"""Tier-0 offline smoke tests for the Recruitment Assistant MVP.

Owned by @qa.eng. These tests are OFFLINE by design: the placeholder
OPENAI_API_KEY in .env means run_recommendation short-circuits with
missing_api_key before any crew build, so no paid LLM call can occur.

Covered checks (map to backend.md / integration.md / SAD section 9):
- App boots; GET /health -> 200 {"status": "ok"}.
- GET / serves index.html; /static/app.js and /static/styles.css -> 200.
- POST /api/recommend contract without a live key -> 503 missing_api_key envelope.
- Validation: missing job_requirements and top_n out of range -> 422.

The full live-LLM shortlist path is intentionally NOT exercised here; it
requires the operator's OPENAI_API_KEY and is recorded as a known gap in qa.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Make the project root importable so "src.app" resolves regardless of cwd.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.app import app  # noqa: E402

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index_served():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "<html" in body.lower()
    assert "/static/app.js" in body
    assert "/static/styles.css" in body


def test_static_app_js():
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
    assert "/api/recommend" in resp.text


def test_static_styles_css():
    resp = client.get("/static/styles.css")
    assert resp.status_code == 200


def test_recommend_missing_api_key_envelope():
    # Placeholder key in .env -> graceful 503 missing_api_key envelope.
    resp = client.post("/api/recommend", json={"job_requirements": "Senior Backend Engineer, Python, FastAPI"})
    assert resp.status_code == 503
    payload = resp.json()
    assert "error" in payload
    assert payload["error"]["code"] == "missing_api_key"
    assert "message" in payload["error"]
    # Fail closed: no partial shortlist leaks on the error path.
    assert "shortlist" not in payload


def test_recommend_missing_job_requirements_422():
    resp = client.post("/api/recommend", json={"top_n": 5})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_recommend_top_n_out_of_range_low_422():
    resp = client.post("/api/recommend", json={"job_requirements": "Backend engineer", "top_n": 0})
    assert resp.status_code == 422
    assert "detail" in resp.json()


def test_recommend_top_n_out_of_range_high_422():
    resp = client.post("/api/recommend", json={"job_requirements": "Backend engineer", "top_n": 99})
    assert resp.status_code == 422
    assert "detail" in resp.json()
