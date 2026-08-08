# Integration: Recruitment Assistant (MVP)

## Overview

This document records the Build-phase integration work for the Recruitment
Assistant MVP, owned by `@integration.eng`. It verifies that the frontend
(`src/static/index.html`, `app.js`, `styles.css`) and the backend
(`src/app.py`, `src/crew.py`) are correctly wired for the MVP recruitment flow
under `AAMAD_TARGET_RUNTIME=crewai`.

Scope is MVP-lean and verification-focused: confirm the same-origin request and
response contract holds end to end, fix any field-name mismatches, and document
what was and was not exercised. No new features were added and no paid LLM calls
were made.

## Integration Approach: same-origin single service

Per SAD sections 1, 3, 4, and 6, the MVP is a single FastAPI process that serves
both the JSON API and the static UI:

- `GET /` serves `src/static/index.html`; `src/static/` is mounted at `/static`
  (so `app.js` and `styles.css` load from the same origin).
- The browser calls `POST /api/recommend` with a relative path via `fetch`. No
  CORS layer exists or is needed because the UI and API share one origin.
- Non-streaming: a single JSON response is returned after the crew run
  completes; the UI uses a busy indicator, not a progressive/streaming renderer.
- Fail closed: on any validation or runtime failure the service returns a
  structured error and the UI renders no partial shortlist.

This matches the crewai adapter (sequential process, non-streaming batch run)
and the SAD single-service decision.

## Request / Response Contract (as wired)

Request (frontend `app.js` -> backend `RecommendRequest` in `app.py`):

- `job_requirements`: string (required). Sent from the textarea.
- `criteria`: string array (optional). Parsed from newline/comma-separated
  input; omitted when blank so the server applies its default behavior.
- `top_n`: integer (optional, default 5, bounds 1-25). Matches the backend
  `Field(default=5, ge=1, le=25)`.
- Content-Type `application/json`, same origin, relative path `/api/recommend`.

Success response (200) consumed by `app.js`:

- `shortlist[]`, each entry: `candidate`, `rank`, `score`, `rationale`,
  `criteria_breakdown[]`.
- `criteria_breakdown[]`, each item: `criterion`, `result`
  (`met` / `partially_met` / `missed`), `evidence`.
- `run_id` (displayed for traceability), `status` ("ok"), optional `notes`.
- Empty-but-valid run: `status: "ok"` with an empty `shortlist` and a `notes`
  message; the UI renders a "No strong matches" block, not an error.

Error responses:

- Custom envelope `{ "error": { "code", "message" } }` for handled failures
  (for example `missing_api_key` at 503, `invalid_input` at 400,
  `runtime_error` at 502). The UI renders `error.message` and `error.code`.
- FastAPI validation failures return `422` with the default
  `{ "detail": [...] }` shape (missing `job_requirements`, `top_n` out of range).
  This is a deliberate backend choice recorded in `backend.md`, not the custom
  envelope. See the fix below for how the frontend now surfaces this shape.

## Verification Results (via FastAPI TestClient, no live LLM key, no paid calls)

Environment: the existing project `.venv` (Python 3.12) with fastapi, uvicorn,
python-dotenv, pydantic, PyYAML, crewai installed (setuptools pinned <80). The
`.env` `OPENAI_API_KEY` is the placeholder value, so the crew never kicks off and
no paid call can occur. The app was booted in-process with
`fastapi.testclient.TestClient`.

1. `GET /` -> 200, serves `index.html` that references `/static/app.js` and
   `/static/styles.css`. `GET /static/app.js` -> 200 and `GET /static/styles.css`
   -> 200. PASS.
2. Field-name alignment (verified by inspecting the served `app.js` against
   `app.py` / `crew.py`): the frontend posts to the exact path `/api/recommend`
   and sends exactly `job_requirements`, `criteria`, `top_n`; it reads exactly
   `shortlist[].{candidate, rank, score, rationale, criteria_breakdown}`, the
   breakdown fields `{criterion, result, evidence}`, `run_id`, `notes`, and the
   `{ error: { code, message } }` envelope. Success and custom-error contracts
   match with no mismatch. PASS.
3. `GET /health` -> 200 `{"status": "ok"}` (boots without an API key). PASS.
4. `POST /api/recommend` with the placeholder key -> 503
   `{"error": {"code": "missing_api_key", "message": ...}}`. The boundary and
   error propagation work end to end: request -> Pydantic validation ->
   `run_recommendation` fail-fast key check -> `RecommendationError` ->
   `_STATUS_BY_CODE` mapping -> envelope. The frontend `handleError` renders this
   envelope (message plus code) and shows no shortlist rows. PASS.
5. Invalid input: `top_n: 0` -> 422, missing `job_requirements` -> 422,
   `top_n: 99` -> 422 (all Pydantic validation). The frontend now surfaces the
   422 `detail` as a readable field-level message (see fix). PASS.

All five checks pass. `node --check` confirms `app.js` remains syntactically
valid after the edit.

## Mismatch Found and Fixed (minimal)

- Found: the success contract and the custom `{ error: { code, message } }`
  envelope were already fully aligned between `app.js` and the backend. No
  field-name mismatch existed there.
- Minor gap on the validation path: FastAPI returns `422` as
  `{ "detail": [...] }`, which does not match the custom error envelope. The
  frontend `handleError` only read `payload.error.*`, so a 422 fell through to a
  generic "The server returned an error (HTTP 422)." message. The error was
  surfaced (no crash, no partial shortlist), but without the field-level guidance
  the SAD calls for (section 4, "reject malformed input ... with guidance").
- Fix (frontend aligned to the backend's actual 422 shape, `src/static/app.js`):
  added a `formatValidationDetail` helper and a `payload.detail` branch in
  `handleError` so a 422 now renders a readable message such as
  "top_n: Input should be greater than or equal to 1" under the code
  `invalid_input`. This is a small, additive change; the custom-envelope path and
  all other states are unchanged.

No backend or contract changes were made. The fix keeps the frontend the single
place that adapts to both error shapes the backend can emit.

## Known Issues and Gaps (honest)

- A full, non-empty shortlist round-trip was NOT exercised. It requires the
  operator's real `OPENAI_API_KEY` and would incur paid LLM calls. What remains
  unverified end to end with a live key: the exact JSON the Recommender returns
  versus the `shortlist` contract, the empty "no strong matches" path against
  live output, and low-temperature scoring reproducibility. The backend
  normalizes and parses defensively (`_extract_json`, `_normalize_shortlist`) and
  the frontend renders defensively (fallbacks for missing fields), so shape drift
  should degrade gracefully rather than crash, but this is asserted from code
  review, not a live run.
- Two error-envelope shapes coexist by design: the custom
  `{ error: { code, message } }` for handled failures and FastAPI's
  `{ detail: [...] }` for 422 validation. The frontend now handles both. If a
  single unified envelope is desired later, add a FastAPI
  `RequestValidationError` handler in `app.py`; deferred as non-MVP.
- Prompt Trace and per-task lifecycle logs under `project-context/2.build/logs`
  (adapter Logging rule) were not produced here because no live crew run was
  performed. Deferred to QA/operator once a key is set.
- The frontend does not explicitly assert `status == "ok"`; it treats HTTP 200
  with no `error` key as success. Functionally correct for the current backend;
  noted for completeness.

## Sources

- `project-context/1.define/prd.md` (authoritative PRD; sections 4, 6 - contract,
  states, HITL).
- `project-context/1.define/sad.md` (pinned architecture; sections 1, 3, 4, 6 -
  single service, frontend, API contract, data flow and error propagation).
- `project-context/2.build/backend.md` (endpoints, error-code/HTTP-status map,
  graceful no-key handling).
- `project-context/2.build/frontend.md` (UI states and field consumption).
- `.cursor/rules/adapter-crewai.mdc` (sequential, non-streaming, fail-closed).
- Code inspected and exercised: `src/app.py`, `src/crew.py`,
  `src/static/index.html`, `src/static/app.js`, `src/static/styles.css`.

## Assumptions

- The `.env` `OPENAI_API_KEY` is a placeholder, so `run_recommendation`
  short-circuits with `missing_api_key` before any crew build; this is the
  intended safe path for verification without a paid call.
- Verification used `TestClient` (in-process ASGI) rather than a live Uvicorn
  server; same-origin behavior and routing are identical for this purpose.
- The candidate object exposes `name`/`title` per `data/candidates.json`; the
  renderer falls back to `id`/`role`/"Candidate N", so exact live shape was not
  required to verify wiring.
- `AAMAD_TARGET_RUNTIME=crewai` is authoritative; the integration is
  non-streaming batch request/response consistent with that adapter.

## Open Questions

- Should the backend emit a single unified error envelope for 422 as well (via a
  `RequestValidationError` handler), or is the two-shape approach acceptable for
  the MVP? (frontend now handles both.)
- Should Prompt Trace and per-task lifecycle logs be persisted under
  `project-context/2.build/logs` during the first keyed run (QA), per the adapter
  Logging rule?
- The full non-empty shortlist round-trip and reproducibility checks remain for
  QA/operator once a valid `OPENAI_API_KEY` is provided. What sample job
  requirements and expected shortlist size define the QA acceptance run?

## Audit

- 2026-08-08, integration.eng, integrate-api, resolved runtime crewai. Verified
  same-origin single-service wiring via FastAPI TestClient with the placeholder
  key (no paid LLM calls): GET / plus /static/app.js and /static/styles.css 200;
  GET /health 200 {"status":"ok"}; POST /api/recommend surfaces the 503
  missing_api_key error envelope; invalid input (top_n=0, top_n=99, missing
  job_requirements) returns 422. Confirmed exact field-name alignment between
  app.js and app.py/crew.py for the request (job_requirements, criteria, top_n),
  the success contract (shortlist[].{candidate, rank, score, rationale,
  criteria_breakdown{criterion, result, evidence}}, run_id, status, notes), and
  the {error:{code,message}} envelope. Applied one minimal frontend fix in
  src/static/app.js: handleError now parses FastAPI's 422 {detail:[...]} shape
  (added formatValidationDetail) so validation errors surface field-level
  guidance under code invalid_input; node --check confirms valid JS. Full
  non-empty shortlist round-trip deferred pending the operator's OPENAI_API_KEY.
