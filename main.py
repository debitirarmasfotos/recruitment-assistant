"""Entry point for the Recruitment Assistant MVP.

Runs the FastAPI app (defined in src/app.py) with Uvicorn. Host and port are
configurable via environment variables and default to 127.0.0.1:8000 for
local single-user safety.

Why loopback by default: the security assessment (security.md, finding H1)
notes that POST /api/recommend has no authentication or rate limiting and
triggers paid LLM calls. Binding to 127.0.0.1 keeps the paid endpoint off any
untrusted network. Do NOT bind to 0.0.0.0 or a public interface until auth,
rate limiting, and provider-side spend caps are in place.

Environment variables:
- APP_HOST  : bind host    (default 127.0.0.1)
- APP_PORT  : bind port    (default 8000)
- APP_ENV   : development | production (default development). In development,
              auto-reload is enabled.

Usage:
    python main.py
"""

from __future__ import annotations

import os

import uvicorn


def _resolve_host() -> str:
    return (os.getenv("APP_HOST") or "127.0.0.1").strip()


def _resolve_port() -> int:
    raw = (os.getenv("APP_PORT") or "8000").strip()
    try:
        return int(raw)
    except ValueError:
        return 8000


def main() -> None:
    host = _resolve_host()
    port = _resolve_port()
    reload_enabled = (os.getenv("APP_ENV") or "development").strip().lower() == "development"

    # Reference the app by import string so reload works; the import string
    # points at the FastAPI instance created in src/app.py.
    uvicorn.run(
        "src.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
    )


if __name__ == "__main__":
    main()
