# Backend Implementation: Recruitment Assistant (MVP)

## Overview

This document records the Build-phase backend implementation for the Recruitment
Assistant MVP, owned by `@backend.eng`. It implements the architecture pinned in
`project-context/1.define/sad.md` for `AAMAD_TARGET_RUNTIME=crewai`: a three-agent
CrewAI sequential crew (Researcher -> Evaluator -> Recommender) exposed through a
single FastAPI service that also serves the static UI.

Scope is MVP-lean. Non-MVP concerns (persistence, auth, CORS, streaming, live
sourcing connectors, ATS integration) are excluded per SAD sections 1 and 8.

## What Was Implemented

Files created (all under the project root):

- `config/agents.yaml` - externalized Researcher, Evaluator, Recommender agent
  definitions. `allow_delegation: false` for all three (SAD section 2). `max_iter: 12`
  per agent (adapter baseline).
- `config/tasks.yaml` - three sequential tasks (`source_task`, `evaluate_task`,
  `recommend_task`) with explicit `context` chaining (source -> evaluate -> recommend)
  and `expected_output` describing plain-JSON shapes without code fences (adapter
  Quality Gates).
- `src/crew.py` - builds the CrewAI `Crew` from the YAML config, `Process.sequential`,
  `memory=False`, `max_rpm=30`. Loads candidates from `data/candidates.json`. Exposes
  `run_recommendation(job_requirements, criteria=None, top_n=5) -> dict`.
- `src/app.py` - FastAPI app: `POST /api/recommend`, `GET /health`, static mount of
  `src/static`, and `index.html` served at `/`. Uses `python-dotenv` to load `.env`.
- `data/candidates.json` - 10 synthetic candidates, clearly fictional names, no real PII.
- `src/static/index.html` - minimal placeholder so the static mount works. The
  frontend engineer will build the real recruiter UI.
- `requirements.txt` - pinned dependencies (see Setup).

### Runtime controls (crewai adapter alignment)

- Process mode: `Process.sequential` (reproducible MVP builds).
- Delegation: `allow_delegation=false` for all agents.
- Temperature: Evaluator and Recommender run at `temperature=0.1` (low, for scoring
  determinism, SAD section 2); Researcher at `0.2`.
- `max_iter=12` per agent; `max_rpm=30` at crew level; `memory=False`.
- Task retry: `max_retries=2` per task for transient LLM errors (adapter baseline
  `max_retry_limit >= 2`).
- LLM: model resolved from `OPENAI_MODEL` (default `gpt-4o`), key from `OPENAI_API_KEY`.

### Application Crew: agents

Externalized in `config/agents.yaml`:

- `researcher` - role "Candidate Sourcing Researcher". Sources matching candidates
  from the provided synthetic pool; never invents candidates. First task; output
  passed to the Evaluator via `Task.context`.
- `evaluator` - role "Candidate Evaluator". Scores each candidate 0-100 and marks each
  criterion `met` / `partially_met` / `missed` with an evidence note. Second task;
  consumes the Researcher output via context; low temperature.
- `recommender` - role "Shortlist Recommender". Ranks candidates and builds the
  shortlist with rationale and per-criterion breakdown. Final task; consumes the
  Evaluator output via context.

### Application Crew: tasks

Externalized in `config/tasks.yaml`, sequential with context chaining:

1. `source_task` (researcher) - selects relevant candidates from the pool.
2. `evaluate_task` (researcher output as context) - scores against criteria.
3. `recommend_task` (evaluate output as context) - ranks and formats the shortlist.

Tie-break (documented, stable, SAD section 2 / PRD section 6): order by score
descending; on effectively equal scores, more fully-met (`met`) criteria first; if
still tied, preserve incoming order. Near-ties are flagged in the rationale.

## API Endpoints (matching the SAD)

- `POST /api/recommend`
  - Request body: `{ "job_requirements": string | object, "criteria"?: [...], "top_n"?: int }`.
    `job_requirements` is required; `criteria` and `top_n` are optional (`top_n`
    defaults to 5, constrained to 1-25).
  - Success (200): `{ "shortlist": [ { "candidate", "rank", "score", "rationale",
    "criteria_breakdown": [ { "criterion", "result", "evidence" } ] } ], "run_id",
    "status": "ok", "notes"? }`.
  - Empty-but-valid run: `status: "ok"` with an empty `shortlist` and a `notes` field
    explaining "no strong matches" (not an error).
  - Failure: `{ "error": { "code": string, "message": string } }` with an appropriate
    HTTP status and NO partial shortlist (fail closed, PRD section 5).
- `GET /health` -> `{ "status": "ok" }`. Boots and responds without an API key.
- `GET /` -> serves `src/static/index.html`. `src/static` mounted at `/static`.

### Error codes and HTTP status mapping

- `invalid_input` -> 400 (business-rule validation in the crew layer).
- Pydantic body validation failures -> 422 (missing `job_requirements`, `top_n < 1`, etc.).
- `missing_api_key` -> 503 (no valid `OPENAI_API_KEY`).
- `runtime_unavailable` -> 503 (crewai not installed).
- `dataset_*` / `config_*` -> 500.
- `output_unparseable` / `runtime_error` -> 502 (LLM/crew failure or unparseable output).
- Any unexpected error -> 500 `internal_error` (stack trace logged, not leaked to client).

### Graceful no-key handling

`run_recommendation` checks for a missing or placeholder `OPENAI_API_KEY` before any
crew build and returns a clear `missing_api_key` error. This lets the app boot and
`/health` and `/` work without a key, and never triggers a paid LLM call by accident.

## How to Run

Prerequisites: Python 3.12, a valid `OPENAI_API_KEY` in `.env` (copy from `.env.example`).

```
# from the project root
python -m venv .venv
.venv/Scripts/activate           # Windows;  source .venv/bin/activate on Unix
pip install -r requirements.txt
# set OPENAI_API_KEY in .env (never commit real keys)
uvicorn src.app:app --reload --port 8000
```

Then open `http://localhost:8000/` (placeholder UI), `GET http://localhost:8000/health`,
or `POST http://localhost:8000/api/recommend`.

## Verification (done without a real OpenAI key)

Environment: Python 3.12.10. A virtualenv was created at `.venv` (gitignored).

Install outcome:

- API-layer deps installed and verified: `fastapi==0.115.6`, `uvicorn==0.34.0`,
  `python-dotenv==1.0.1`, `pydantic==2.10.4`, `PyYAML==6.0.3` (plus `httpx` for the
  test client).
- Full runtime installed and verified: `crewai==0.86.0` (pulls `litellm==1.95.0`).
- Required fix: crewai 0.86 imports `pkg_resources`, which was removed in setuptools
  81+. The Python 3.12 venv shipped setuptools 84, so `import crewai` failed until
  setuptools was pinned below 80 (`setuptools==79.0.1`). This pin is now recorded in
  `requirements.txt`.

Smoke checks (all passed, no paid LLM calls):

- `GET /health` -> `200 {"status": "ok"}`.
- `GET /` -> `200`, serves the placeholder `index.html`.
- Crew build (no kickoff): `build_crew(...)` constructs 3 agents
  (Candidate Sourcing Researcher, Candidate Evaluator, Shortlist Recommender), 3 tasks,
  `Process.sequential`, `allow_delegation=[False, False, False]`, and context chain
  lengths `[0, 1, 1]` (source has none; evaluate depends on source; recommend depends
  on evaluate). YAML config and `data/candidates.json` (10 candidates) load cleanly.
- `POST /api/recommend` with no real key -> `503 {"error": {"code": "missing_api_key",
  ...}}` (graceful, no crash, no partial shortlist).
- `POST /api/recommend` with `top_n: 0` or missing `job_requirements` -> `422` (Pydantic
  validation).

## What Needs the User's OPENAI_API_KEY

The following were NOT run because they require a valid key and would incur paid LLM
calls. They are expected to be exercised by QA and the operator once a key is set:

- A full `crew.kickoff()` end-to-end run producing a real ranked shortlist.
- Verification of the JSON shape actually returned by the Recommender against the API
  `shortlist` contract (the code parses and normalizes the output; the exact prose and
  scores depend on the live model).
- Reproducibility / low-temperature scoring behavior across repeated identical runs.

## Sources

- `project-context/1.define/prd.md` (authoritative PRD; sections 3, 4, 5, 6).
- `project-context/1.define/sad.md` (pinned architecture; sections 2, 4, 6, 8).
- `.cursor/rules/adapter-crewai.mdc` (CrewAI adapter rules: Mapping, Execution, Tools,
  Quality Gates, Memory).
- `.env.example` and `aamad.config.example.yml` (env var names, project preferences).

## Assumptions

- `OPENAI_MODEL` defaults to `gpt-4o` when unset (SAD Assumptions).
- Default `top_n` is 5 (SAD Open Question; a sensible MVP default, bounded to 1-25).
- Default criteria: when `criteria` is omitted, the Researcher/Evaluator infer
  sensible job-relevant criteria from the requirements. The specific approved rubric
  remains a PRD/SAD Open Question.
- The Researcher reads the local dataset via the crew inputs (candidate pool passed in
  the prompt) rather than a bound file-read tool; this keeps the MVP tool surface at
  least privilege with no external tools, consistent with SAD section 2.
- `setuptools<80` is a transitive requirement for crewai 0.86 on Python 3.12; recorded
  in `requirements.txt`.
- The synthetic dataset has 10 candidates skewed toward software engineering roles; a
  representative size/structure is a PRD Open Question.

## Open Questions

- Which specific job-relevant criteria and scoring rubric should the Evaluator use, and
  who approves them? (PRD / SAD)
- What default `top_n` should the shortlist use when omitted? (currently 5)
- What scoring-consistency threshold (variance across identical runs) is acceptable?
- What structure and size should `data/candidates.json` have to be representative?
- Should Prompt Trace and per-task lifecycle logs be persisted under
  `project-context/2.build/logs` now, or is that deferred to the Integration/QA epics?
  (adapter Logging rule references it; no live run was performed here.)

## Audit

- 2026-08-08, backend.eng, develop-be, resolved AAMAD_TARGET_RUNTIME=crewai. Implemented
  config/agents.yaml, config/tasks.yaml, src/crew.py, src/app.py, data/candidates.json,
  src/static/index.html, requirements.txt. Resolved LLM model default `gpt-4o`
  (`OPENAI_MODEL`), Evaluator/Recommender temperature 0.1, Researcher temperature 0.2,
  max_iter=12, max_rpm=30, task max_retries=2, memory=False. Verified `GET /health`
  200 and crew construction offline; full LLM run deferred pending `OPENAI_API_KEY`.
  Installed and verified crewai==0.86.0, fastapi==0.115.6, uvicorn==0.34.0,
  python-dotenv==1.0.1, pydantic==2.10.4, PyYAML==6.0.3, litellm==1.95.0,
  setuptools==79.0.1.
