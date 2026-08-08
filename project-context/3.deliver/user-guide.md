# User Guide: Recruitment Assistant (MVP)

## 1. Product Overview

The Recruitment Assistant is a multi-agent tool that turns a set of job
requirements into a ranked candidate shortlist with per-criterion reasoning. It
runs a three-agent CrewAI sequential crew: a Researcher sources candidate
profiles from the bundled dataset, an Evaluator scores each candidate against the
criteria you provide, and a Recommender ranks the top matches and writes an
evidence-based rationale for each one. The three stages hand context forward in
order, so every recommendation is traceable back to the scores and evidence
produced upstream. The whole thing is served as a single local web service: one
FastAPI process exposes both a simple web page and a JSON API on the same origin.

It is built for recruiters (in-house or agency) and hiring managers who want a
faster, more consistent first pass at a candidate pool without giving up control
of the decision. The assistant recommends; it never auto-rejects or contacts
anyone.

**MVP limitations and known gaps (read these before you rely on the output):**

- **Local, single-user only.** The service has no authentication and no rate
  limiting, so it is intended to run on your own machine bound to loopback
  (`127.0.0.1`). Do not expose it on a shared or public network in this state.
- **Synthetic data only.** Candidates come from a bundled fictional dataset
  (`data/candidates.json`, 10 invented profiles). No real candidate data is used
  or stored.
- **A live shortlist needs an OpenAI API key.** Without a valid key the service
  boots and serves the UI, but a recommendation request returns a clear
  `missing_api_key` error instead of a paid LLM call. The live end-to-end
  shortlist path has not been verified against real model output; it is a
  documented, scoped gap, not a defect.
- **The human makes the final hiring decision.** The shortlist is a
  recommendation with rationale for review, not an automated hiring decision.

## 2. Prerequisites

- **Runtime:** Python 3.9 or later. The build and tests were run on Python 3.12;
  note that `crewai==0.86.0` requires `setuptools<80` on Python 3.12 (this pin is
  already in `requirements.txt`).
- **Tools:** `git` to obtain the code; optionally Docker if you prefer the
  container path.
- **Account / key:** an OpenAI API key to run a live recommendation. It is
  supplied through the environment variable `OPENAI_API_KEY` (name only; never
  commit the value). Optional related variables: `OPENAI_MODEL`,
  `AAMAD_TARGET_RUNTIME`, `APP_NAME`, `APP_ENV`, `CREWAI_TELEMETRY_OPT_OUT`,
  `CREWAI_TRACING_ENABLED`, `CREWAI_VERBOSE`, `LOG_LEVEL`. Host and port can be
  set with `APP_HOST` and `APP_PORT`.
- **Client:** a modern web browser for the web UI. No other client is required.

## 3. Installation

These steps follow the local Python path from the deploy runbook. Run them from
the project root.

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv/Scripts/activate          # Windows;  source .venv/bin/activate on Unix
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create your local config from the template and set your key:
   ```
   cp .env.example .env            # then set OPENAI_API_KEY in .env (never commit)
   ```
   Open `.env` and replace the placeholder `OPENAI_API_KEY=your_openai_api_key_here`
   with a real key. Leave the other variables at their defaults unless you need to
   change them. `.env` is gitignored and must never be committed.
4. Verify the install with a health smoke check. Start the app (see Getting
   Started) and confirm:
   ```
   GET /health  ->  200  {"status": "ok"}
   ```
   Health returns `ok` even without a key, so a passing health check confirms the
   process booted, not that a key is set.

Docker is an optional alternative: with `.env` present, `docker compose build`
then `docker compose up -d` publishes the same app on `127.0.0.1:8000`. See the
deploy runbook for the full Docker path.

## 4. Getting Started

First-run walkthrough of the primary flow.

1. **Start the app** from the project root with your `.venv` active:
   ```
   python main.py
   ```
   By default it serves on `http://127.0.0.1:8000/` (host and port are
   configurable via `APP_HOST` / `APP_PORT`).
2. **Open the UI** in your browser at `http://127.0.0.1:8000`. The page is a
   single form served by the same service that runs the crew.
3. **Enter your inputs:**
   - **Job requirements** (required): a free-text description of the role in the
     main text area, for example "Senior Python engineer, 5+ years, FastAPI and
     cloud, strong testing".
   - **Criteria** (optional): the job criteria to score against, entered one per
     line or comma-separated, for example Python, FastAPI, Cloud, Testing. If you
     leave this blank the server applies its default behavior.
   - **top_n** (optional): how many candidates to return in the shortlist.
     Defaults to 5; must be between 1 and 25.
4. **Submit.** The UI shows a busy indicator while the crew runs. This is a
   single, non-streaming request: results appear once the full run completes,
   not progressively.
5. **Read the shortlist.** On success the page renders a ranked list. Each entry
   shows the candidate, their rank, an overall score, a written rationale, and a
   per-criterion breakdown listing each criterion as met, partially met, or
   missed with the supporting evidence. A run identifier (`run_id`) is displayed
   for traceability, and a reminder that the human makes the final decision is
   shown with the results.

## 5. Everyday Use

Common tasks and how to read what comes back.

- **Refining criteria.** If the shortlist does not reflect what matters for the
  role, adjust the criteria list and resubmit. Explicit, job-relevant criteria
  give the Evaluator clearer targets and produce a more useful per-criterion
  breakdown.
- **Reading scores and rationale.** Use the per-criterion breakdown (met /
  partially met / missed with evidence) to see the "why" behind a ranking rather
  than trusting the overall score alone. Every recommendation traces back to the
  evidence the Evaluator recorded, so you can sanity-check each claim against the
  candidate profile before advancing anyone.
- **"No strong matches" (empty result).** A valid run that finds no strong
  candidates returns successfully with an empty shortlist and a short notes
  message. The UI renders a "No strong matches" block. This is a normal outcome,
  not an error, and it means the crew ran but nothing cleared the bar for your
  criteria.
- **`503 missing_api_key`.** If you submit a recommendation without a valid
  `OPENAI_API_KEY`, the service returns a 503 with a clear message telling you to
  set the key in `.env`. This is fail-closed by design: no partial shortlist and
  no accidental paid call. Set a real key and resubmit. The health page and UI
  keep working without a key.
- **`422` validation errors.** If an input is invalid (for example `top_n` set to
  0, `top_n` above 25, or missing job requirements) the service returns a 422 and
  the UI shows a readable field-level message such as "top_n: Input should be
  greater than or equal to 1". Correct the flagged field and resubmit.

## 6. Troubleshooting

- **App will not start (local).** Confirm the `.venv` is active and
  `pip install -r requirements.txt` completed. `crewai==0.86.0` needs
  `setuptools<80` on Python 3.12 (it imports `pkg_resources`, removed in
  setuptools 81+); this pin is already in `requirements.txt`. If `import crewai`
  fails, verify setuptools is below 80 in the venv.
- **`503 missing_api_key` on recommend.** `OPENAI_API_KEY` is unset or still the
  placeholder (`your_openai_api_key_here`). Set a real key in `.env` and restart.
  `/health` and `/` keep working without a key, so this is expected until you add
  the key.
- **Port already in use (`8000`).** Another process holds the port. Either stop it
  or change the port: locally with `APP_PORT=8001 python main.py`; with Docker by
  editing the compose `ports` host side (for example `127.0.0.1:8001:8000`).
- **Docker build fails.** Build from the project root (the Dockerfile copies
  `requirements.txt`, `main.py`, `src/`, `config/`, `data/`). Confirm the base
  image `python:3.12-slim` is pullable and that `.dockerignore` is not excluding a
  path the Dockerfile copies.
- **Docker health check failing.** Check `docker compose logs -f app`; a common
  cause is a missing or invalid `.env` so the container app cannot start. Because
  `/health` does not need a key, a failing health check usually means the process
  did not boot.
- **Where the logs are.** The app writes structured logs to two places: standard
  output (your terminal, or `docker compose logs -f app`) and the file
  `logs/app.log` (the `logs/` directory is created at runtime and is gitignored).
  Each request logs a `received` line and a terminal `ok` / `failed` / `error`
  line carrying a `run_id`, HTTP status, and duration. Failures include a
  machine-readable `code` (for example `missing_api_key`, `runtime_error`,
  `output_unparseable`). Secrets and full candidate data are never logged: the key
  is recorded only as `api_key_present=<bool>` and job requirements only as a
  length-bounded summary.

## 7. Deployment Notes (operators)

For install, start/stop, environment variable matrix, access control, monitoring,
and the full runbook, see `project-context/3.deliver/deploy.md`. Key operator
points:

- **Hosting.** Smallest MVP target: a single service, no database. Two supported
  paths, both local by default: local Python via `main.py`, or Docker via the
  provided `Dockerfile` and `docker-compose.yml`. Both bind host loopback
  (`127.0.0.1:8000`).
- **Access control gate (security H1).** `POST /api/recommend` has no auth and no
  rate limiting and triggers paid LLM calls. This is accepted only for local,
  single-user use on loopback. Before binding to any non-loopback interface or
  sharing the service you must add authentication, per-client rate limiting, a
  request timeout, and a provider-side LLM spend cap.
- **Rollback (high level).** There is no database and no migrations, so rollback
  is a code-and-image revert: identify the last known-good commit or tag, revert
  or check it out, rebuild and restart (local: reinstall if dependencies changed,
  then restart `main.py`; Docker: `docker compose build` then
  `docker compose up -d`), and confirm `GET /health` returns `200 {"status":
  "ok"}`. The synthetic dataset is versioned with the code and `.env` is
  unaffected. See deploy.md for the full procedure.

## Sources

- `project-context/1.define/prd.md` (product scope, features, HITL, MVP limits).
- `project-context/3.deliver/deploy.md` (install/start/stop/rollback, env matrix,
  monitoring, troubleshooting, access control).
- `project-context/3.deliver/execution-results.md` (real run behavior, health,
  static UI, 503 missing_api_key, 422 validation, response contract).
- `project-context/2.build/integration.md` (request/response contract, UI states,
  error shapes).
- `project-context/2.build/qa.md` (Tier-0 smoke results, known gaps, verdict).
- `project-context/2.build/security.md` (MVP posture: local single-user, no auth,
  synthetic data).
- `.env.example` (environment variable names).

## Assumptions

- The MVP runs locally on a single operator machine bound to `127.0.0.1:8000`
  (default), with a real `OPENAI_API_KEY` present only in a gitignored `.env`.
- The candidate dataset stays synthetic (`data/candidates.json`, 10 fictional
  profiles); no real candidate PII is introduced.
- The model defaults to `gpt-4o` when `OPENAI_MODEL` is unset.
- Python 3.9+ is the stated minimum; the build and tests were verified on Python
  3.12 with `setuptools<80`.
- The live end-to-end shortlist path is exercised by the user once a valid key is
  set; the offline surface (health, UI, validation, fail-closed no-key path) is
  verified in QA and execution results.

## Open Questions

- What sample job requirements and expected shortlist size define a good first
  keyed acceptance run? (carried from qa.md and integration.md)
- Live shortlist quality, low-temperature scoring reproducibility, and cost per
  requisition remain to be measured once a real key is supplied. (carried from
  execution-results.md)
- If the service is ever exposed beyond a local demo, which auth mechanism and
  rate-limit policy are required, and who owns the provider-side spend cap?
  (carried from security.md / deploy.md)

## Audit

- 2026-08-08, devops-eng, document-user-guide, resolved AAMAD_TARGET_RUNTIME=crewai.
  Authored `project-context/3.deliver/user-guide.md` following the
  `.cursor/templates/user-guide-template.md` headings (Product Overview,
  Prerequisites, Installation, Getting Started, Everyday Use, Troubleshooting,
  Deployment Notes, then Sources / Assumptions / Open Questions / Audit). Content
  derived only from prd.md, deploy.md, execution-results.md, integration.md,
  qa.md, security.md, and `.env.example` (env var names only). No secrets, no
  invented features, no fabricated screenshots.
