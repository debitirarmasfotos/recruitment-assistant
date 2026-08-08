# Deploy Runbook: Recruitment Assistant (MVP) - Tier-0

## Overview

This is the consolidated Tier-0 deploy runbook for the Recruitment Assistant
MVP, owned by `@devops.eng`, under `AAMAD_TARGET_RUNTIME=crewai`. It packages the
validated MVP for delivery: local Python and Docker hosting, environment
variable matrix, install/start/stop/rollback steps, access-control notes, a
monitoring placeholder, and troubleshooting.

Scope is deploy configuration and runbook only. No live deploy is triggered and
no application logic is changed. The single-service FastAPI app (API plus static
UI) is delivered per SAD section 5 (DevOps and Deployment Architecture).

## Release Scope / Version Summary

- **Product**: Recruitment Assistant MVP. A three-agent CrewAI sequential crew
  (Researcher -> Evaluator -> Recommender) exposed through a single FastAPI
  service that also serves the static single-page UI.
- **Version**: `0.1.0` (from `FastAPI(title="Recruitment Assistant", version="0.1.0")`).
- **Phase status**: Define (PRD, SAD), Build (backend, frontend, integration, QA,
  security), and Deliver (this runbook and deploy config) are complete for the
  MVP. This release delivers deploy artifacts only.
- **Runtime**: `AAMAD_TARGET_RUNTIME=crewai`.
- **Git state (conceptual, not a pinned hash)**: release corresponds to the
  current `main` line with all Build-phase artifacts committed and the deploy
  artifacts added in this step. Use the tip of `main` at delivery time as the
  release point; tag it (for example `v0.1.0`) before any promotion.
- **QA gate**: `project-context/2.build/qa.md` verdict is PASS with scoped gaps
  (Tier-0 offline smoke; 8/8 pytest, data sanity, crew assembly). The live-LLM
  end-to-end shortlist path is unverified by design (needs the operator key) and
  is carried as a known gap below.
- **Security gate**: `project-context/2.build/security.md` verdict is SHIP for the
  synthetic-data local MVP. Carried items: H1 (no auth / rate limiting on the
  paid endpoint - accepted for local single-user only), M2 (unbounded input
  size), and L2 (log-redaction hygiene for the monitoring step). See Access
  Control and Future Work.

### Release scope: in vs out

- In scope: local Python run (`main.py`), Docker image and compose stack, env-var
  matrix, install/start/stop/rollback, access-control policy notes, troubleshooting.
- Out of scope (Future Work): CI/CD pipeline files, live deploy, auth / rate
  limiting, monitoring and CrewAI tracing detail, autoscaling, multi-region.

## Deploy Artifacts (this step)

Created at the project root:

- `main.py` - Uvicorn entry point importing `src.app:app`. Host/port via
  `APP_HOST` / `APP_PORT`, default `127.0.0.1:8000`. Auto-reload when
  `APP_ENV=development`.
- `Dockerfile` - `python:3.12-slim` base; installs `requirements.txt`; copies
  `main.py`, `src/`, `config/`, `data/`; exposes `8000`; runs Uvicorn. No secrets
  baked in.
- `docker-compose.yml` - single `app` service; publishes on host loopback
  (`127.0.0.1:8000:8000`); `env_file: .env`; health check on `GET /health`.
- `.dockerignore` - excludes `.venv`, `.git`, `__pycache__`, `.env`, `tests/`,
  and `project-context/` (docs not needed in the image).

## Hosting Approach

Smallest MVP-appropriate target: a single service, no database, no separate
frontend host. Two supported paths, both local by default.

### Option A - Local Python (simplest)

Runs directly in the project `.venv` via `main.py`. Best for development and the
single-operator demo. Binds `127.0.0.1:8000` by default.

### Option B - Docker (single service)

Runs the same app in a `python:3.12-slim` container via the Dockerfile, with the
compose stack publishing only on host loopback. Best for a reproducible,
isolated run. Health check via `GET /health`.

- Assumed hosting target: single host, single container / process.
- Assumed port: `8000` (host loopback in both options).
- Health-check endpoint: `GET /health` -> `{"status": "ok"}` (boots without a key).

## Environment Variable Matrix

All keys below are the names documented in `.env.example`. No secret values
appear here or in any committed file. Copy `.env.example` to `.env` and set
values locally; `.env` is gitignored.

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `OPENAI_API_KEY` | LLM provider key used by CrewAI / litellm to run the crew. Without a valid value, `POST /api/recommend` returns `503 missing_api_key` and no paid call occurs. | Required to run a recommendation. Optional to boot `/health` and `/`. |
| `OPENAI_MODEL` | Model the crew uses. Defaults to `gpt-4o` when unset. | Optional (default `gpt-4o`). |
| `AAMAD_TARGET_RUNTIME` | Runtime target for the app. Must be `crewai`. | Optional (default `crewai`). |
| `APP_NAME` | Human-readable app name. | Optional. |
| `APP_ENV` | `development` or `production`. `development` enables Uvicorn auto-reload in `main.py`. | Optional (default `development`). |
| `CREWAI_TELEMETRY_OPT_OUT` | Set `true` to opt out of CrewAI telemetry. | Optional (recommended `true`). |
| `CREWAI_TRACING_ENABLED` | Set `true` to send run traces to `app.crewai.com` (requires `crewai login`). Off by default so offline/local runs and tests make no network/auth calls. | Optional (default `false`). |
| `CREWAI_VERBOSE` | Crew console verbosity. | Optional (default `true`). |
| `LOG_LEVEL` | App log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). | Optional (default `INFO`). |

Not stored in `.env.example` but read by `main.py` for host/port control (safe,
non-secret; documented here for completeness): `APP_HOST` (default `127.0.0.1`)
and `APP_PORT` (default `8000`).

## Install, Start, Stop, Rollback

### Local Python (Option A)

Install:

```
# from the project root
python -m venv .venv
.venv/Scripts/activate          # Windows;  source .venv/bin/activate on Unix
pip install -r requirements.txt
cp .env.example .env            # then set OPENAI_API_KEY in .env (never commit)
```

Start:

```
python main.py
# serves http://127.0.0.1:8000/  (UI),  /health,  and POST /api/recommend
```

Stop:

```
# Ctrl+C in the terminal running main.py
```

### Docker (Option B)

Install / build:

```
# from the project root, with .env present (copied from .env.example)
docker compose build
```

Start:

```
docker compose up -d
# published on http://127.0.0.1:8000/  (host loopback only)
docker compose logs -f app        # follow logs
```

Stop:

```
docker compose down
```

### Rollback

The MVP has no database and no migrations, so rollback is a code-and-image
revert:

1. Identify the last known-good commit or tag (for example the previous release
   tag on `main`).
2. Revert or check it out:
   - `git revert <merge_commit>` (preferred: keeps history), or
   - `git checkout <previous_tag_or_commit>` for a detached known-good state.
3. Rebuild and restart:
   - Local: reinstall if dependencies changed (`pip install -r requirements.txt`),
     then restart `python main.py`.
   - Docker: `docker compose build` then `docker compose up -d` (rebuilds the
     image from the reverted code).
4. Confirm health: `GET /health` returns `200 {"status": "ok"}`.

There is no stateful data to migrate back; `data/candidates.json` is synthetic
and versioned with the code. `.env` is unaffected by rollback.

## Access Control (MVP scope)

- **Posture**: local, single-user, no authentication. This is the accepted MVP
  scope in `security.md` (H1 accepted risk) and SAD section 8 (AuthN/AuthZ
  deferred). Both `main.py` and the compose publish target default to host
  loopback (`127.0.0.1`) so the unauthenticated, paid-LLM endpoint is not
  reachable from untrusted networks.
- **security.md H1 (High) - required before any shared or public exposure**:
  `POST /api/recommend` has no auth and no rate limiting and triggers paid LLM
  calls. Before binding to a non-loopback interface (for example Uvicorn or
  compose on `0.0.0.0`) or sharing the service, you MUST add: authentication (at
  minimum a shared API key or reverse-proxy auth), per-client rate limiting, a
  request timeout, and provider-side LLM spend caps. Do not change the publish
  target to `8000:8000` until these are in place.
- **Secrets**: referenced by environment variable name only (`OPENAI_API_KEY`
  and the rest of the matrix above). No secret values are committed. `.env` is
  gitignored and excluded from the Docker image via `.dockerignore`; the image
  receives secrets only at run time via `--env-file .env` / `env_file: .env`.
- **Least privilege**: use an LLM API key scoped to the minimum needed and set a
  provider-side spend limit even for local use.
- Enterprise IAM, SSO, and network segmentation are deferred to Future Work
  (not scoped in PRD/SAD for the MVP).

## Monitoring and Observability

Observability for the MVP is structured application logging plus optional CrewAI
tracing. Both are runtime-aligned to `AAMAD_TARGET_RUNTIME=crewai` and honor the
security.md L2 redaction policy (no secrets, no full PII / requirements).

### What to monitor

- **Liveness / health**: `GET /health` -> `200 {"status": "ok"}`. Used by the
  Docker compose health check; poll it as the up/down signal.
- **Request outcomes**: each `POST /api/recommend` logs a `received` line and a
  terminal `ok` / `failed` / `error` line carrying the request `run_id`, HTTP
  `status`, candidate count (on success), and `duration_ms`. Watch the ratio of
  `failed`/`error` to `ok` as the error rate.
- **Error rate and error codes**: `failed` lines include the machine-readable
  `code` (for example `missing_api_key`, `runtime_error`, `output_unparseable`).
  A rising `runtime_error` / `output_unparseable` rate indicates an LLM or parse
  problem; a spike in `missing_api_key` indicates a misconfigured key.
- **Crew run duration**: `crew execution start` / `crew execution finished`
  (with `run_id`) in `crew.py`, plus `crew stage completed` per agent stage
  (sourcing, evaluating, recommending). Compare against the request `duration_ms`
  to locate slow stages.
- **LLM cost signal**: there is no billing meter in the MVP, so use proxy
  signals: the count of successful `crew execution finished` lines (each is one
  paid three-agent run) and `output_len` per stage. Set a provider-side spend
  cap (see Access Control) as the hard cost guardrail.

### Log levels and storage

- Level is set by `LOG_LEVEL` (default `INFO`; use `DEBUG` for verbose triage).
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`.
- Two sinks, configured once in `src/logging_config.py`:
  - **stdout** via a `StreamHandler` (captured by `docker compose logs -f app`
    or the local terminal).
  - **`logs/app.log`** via a `FileHandler`. The `logs/` directory is created at
    runtime if missing and is gitignored (`logs/` in `.gitignore`), so runtime
    logs are never committed.
- Levels in use: `INFO` for startup, request lifecycle, and crew stages;
  `WARNING` for handled `RecommendationError` outcomes; `ERROR` /
  `logger.exception` for unexpected failures (server-side only, never returned
  to the client).

### Redaction policy (security.md L2)

- The API key is never logged; startup logs only `api_key_present=<bool>`.
- `job_requirements` is logged only as a length-bounded summary
  (`summarize_text`: character length plus a short truncated preview), never the
  full text.
- Candidate records are never logged; crew stage logs carry only the agent role
  (from config, not PII) and an output character length, not content.
- Exception handlers log the exception type / message server-side and must not
  emit secrets; if the system is ever pointed at real data, keep this policy and
  drop the requirements preview.

### CrewAI tracing (optional, opt-in)

Tracing is off by default so offline/local runs and tests make no network or
auth calls. `crew.py` reads `CREWAI_TRACING_ENABLED` and passes `tracing=True`
to the `Crew` only when that flag is truthy. To enable and view traces:

1. Install the tooling extras: `pip install "crewai[tools]"`.
2. Authenticate once: `crewai login` (opens the CrewAI auth flow).
3. Enable tracing: set `CREWAI_TRACING_ENABLED=true` in `.env` (equivalent to
   `tracing=True` on the `Crew`).
4. Run a keyed recommendation, then view traces at `app.crewai.com` -> Traces:
   agent decisions, the task timeline (sourcing -> evaluating -> recommending),
   tool usage, LLM calls, and errors.

Tracing is a network- and cost-relevant control: enable it only with operator
authorization and a provider-side spend cap in place, and keep it off for
offline smoke tests.

## Troubleshooting

- **App will not start (local)**: confirm the `.venv` is active and
  `pip install -r requirements.txt` completed. `crewai==0.86.0` requires
  `setuptools<80` on Python 3.12 (it imports `pkg_resources`, removed in
  setuptools 81+); this pin is already in `requirements.txt`. If `import crewai`
  fails, verify setuptools is below 80 in the venv.
- **`503 missing_api_key` from `POST /api/recommend`**: `OPENAI_API_KEY` is unset
  or still the placeholder (`your_openai_api_key_here`). Set a real key in `.env`.
  This is fail-closed by design (no accidental paid call); `/health` and `/` keep
  working without a key.
- **Docker build fails**: ensure you build from the project root (the Dockerfile
  copies `requirements.txt`, `main.py`, `src/`, `config/`, `data/`). Confirm the
  base image `python:3.12-slim` is pullable and that `.dockerignore` is not
  excluding a path the Dockerfile copies.
- **Port already in use (`8000`)**: another process holds the port. Either stop it
  or change the port: local via `APP_PORT=8001 python main.py`; Docker by editing
  the compose `ports` host side (for example `127.0.0.1:8001:8000`).
- **Docker health check failing**: check `docker compose logs -f app`; a common
  cause is a missing or invalid `.env` so the container app cannot start. Note
  that `/health` itself does not need a key, so a failing health check usually
  means the process did not boot.

## Sources

- `project-context/1.define/prd.md` (MVP scope, security section 5, section 8).
- `project-context/1.define/sad.md` (section 4 API, section 5 DevOps and
  Deployment, section 8 Security).
- `project-context/2.build/qa.md` (Tier-0 smoke, PASS with scoped gaps).
- `project-context/2.build/security.md` (verdict SHIP; H1, M2, L2 carried items).
- `project-context/2.build/backend.md` (app/crew implementation, run steps, deps).
- `src/app.py`, `src/crew.py`, `requirements.txt`, `.env.example`, `.gitignore`.
- `.claude/rules/delivery-workflow.md`, `.claude/rules/adapter-crewai.md`.

## Assumptions

- Security status: `security.md` verdict is SHIP for the synthetic-data local MVP,
  with H1 (no auth / rate limiting on the paid endpoint) explicitly accepted for
  local single-user scope only. This runbook carries H1, M2, and L2 as gates
  before any shared/public exposure or real-data use.
- No live deploy is triggered by this step; deploy configuration and runbook only
  are produced. Any promotion to a shared or public environment requires explicit
  operator authorization and the H1 controls above.
- Hosting target is a single host/process on loopback `127.0.0.1:8000`; the
  container binds `0.0.0.0` internally (required for reachability) while compose
  publishes only on host loopback.
- Model defaults to `gpt-4o` when `OPENAI_MODEL` is unset (SAD Assumptions).
- The dataset stays synthetic (`data/candidates.json`, 10 fictional profiles); no
  real candidate PII is introduced during the mini-project.
- `.env` exists locally (copied from `.env.example`) and remains gitignored.

## Open Questions

- What is the intended deployment surface beyond the local demo (loopback-only vs
  a shared/hosted service)? This determines whether H1 must be resolved before any
  further deploy. (carried from security.md)
- Which auth mechanism and rate-limit policy are required for shared exposure, and
  who owns the LLM provider-side spend cap? (carried from security.md)
- Should input size caps (M2) be added before broader deploy or tracked as
  follow-up? (carried from security.md)
- What sample job requirements and expected shortlist size define the keyed QA
  acceptance run before a wider release? (carried from qa.md)

## Audit

- 2026-08-08, devops-eng, define-deploy, resolved AAMAD_TARGET_RUNTIME=crewai.
  Created deploy artifacts at the project root: main.py (Uvicorn entry point
  importing src.app:app, default 127.0.0.1:8000), Dockerfile (python:3.12-slim,
  installs requirements, copies main.py/src/config/data, exposes 8000, runs
  Uvicorn, no baked secrets), docker-compose.yml (single app service, publishes
  127.0.0.1:8000:8000, env_file .env, /health health check), and .dockerignore
  (excludes .venv, .git, __pycache__, .env, tests, project-context). Authored this
  Tier-0 deploy runbook. Confirmed QA gate (qa.md PASS with scoped gaps) and
  security gate (security.md SHIP for the synthetic-data local MVP), carrying H1
  (auth/rate-limit), M2 (input-size), and L2 (log-redaction) as gates/future work.
  Verified offline in the project .venv (Python 3.12): main.py imports the FastAPI
  app and resolves default host 127.0.0.1 / port 8000; a TestClient GET /health
  returned 200 {"status":"ok"}; all Dockerfile-referenced paths (requirements.txt,
  main.py, src, config, data) exist. Docker is unavailable in this environment, so
  the Dockerfile and compose stack are provided but NOT built here; a docker build
  and live deploy are deferred pending operator authorization. No application code
  was modified and no paid LLM call was made.
- 2026-08-08, devops-eng, document-deploy, resolved AAMAD_TARGET_RUNTIME=crewai.
  Added observability to the MVP without changing the API contract or crew logic.
  Implemented structured logging in src/logging_config.py (level from LOG_LEVEL,
  format '%(asctime)s - %(name)s - %(levelname)s - %(message)s', StreamHandler +
  FileHandler to logs/app.log, logs/ created at runtime and gitignored). src/app.py
  now logs startup (app/version/env/runtime/model and api_key_present as a boolean
  only), and per-request received/ok/failed/error lines with a request run_id, a
  length-bounded job_requirements summary (summarize_text), top_n, status,
  candidate count, and duration_ms. src/crew.py logs crew execution start/finish
  (run_id) and per-stage completion via a task_callback (agent role + output length
  only, no PII), and reads CREWAI_TRACING_ENABLED (default off) to pass tracing=True
  to the Crew only when opted in, plus CREWAI_VERBOSE for verbose control. Added
  CREWAI_TRACING_ENABLED and LOG_LEVEL to .env.example and logs/ to .gitignore.
  Expanded this Monitoring and Observability section (what to monitor, log levels
  and storage, L2 redaction policy, and CrewAI tracing setup/viewing at
  app.crewai.com). Verified offline in the project .venv (no paid LLM calls):
  src/app.py and src/crew.py import cleanly, TestClient GET /health returns 200,
  a log line is emitted to logs/app.log and stdout, and pytest tests/test_smoke.py
  passes 8/8. Tracing network calls were NOT enabled and the paid LLM path was NOT
  run.
