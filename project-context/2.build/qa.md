# QA: Recruitment Assistant (MVP) - Tier-0 Smoke

## Overview

This document records the Build-phase QA smoke pass for the Recruitment Assistant
MVP, owned by `@qa.eng`, under `AAMAD_TARGET_RUNTIME=crewai`. It validates only
what is present in the current build. The pass is a Tier-0 offline smoke: it
verifies the request/response boundary, static serving, validation, data sanity,
and crew assembly WITHOUT any paid LLM call.

The full live-LLM path (a `crew.kickoff()` producing a real ranked shortlist) is
NOT verified here. It requires the operator's `OPENAI_API_KEY` and would incur
paid calls. This is recorded as a known gap / future work, not a failure.

## Scope

In scope (offline, no paid calls):

- App boot and liveness (`GET /health`).
- Static single-page serving (`GET /`, `/static/app.js`, `/static/styles.css`).
- `POST /api/recommend` request-boundary contract without a live key (graceful
  `missing_api_key` 503 envelope).
- Server-side validation (missing `job_requirements`, `top_n` out of range -> 422).
- Data sanity of `data/candidates.json` (count, fields, synthetic PII check).
- Crew assembly (3 agents, sequential process, `allow_delegation=false`, context
  chaining) without a kickoff.
- A committed pytest smoke suite (`tests/test_smoke.py`) for checks 1-4.

Out of scope (deferred, see Known Gaps):

- Live-LLM end-to-end run producing a non-empty ranked shortlist.
- Empty "no strong matches" path against live Recommender output.
- Low-temperature scoring reproducibility across identical runs.
- Load/performance, concurrency, security assessment (owned by `@security.eng`).

## Environment

- Platform: Windows 11, Python 3.12.10 (project `.venv`, gitignored).
- Runtime target: `AAMAD_TARGET_RUNTIME=crewai` (resolved).
- Key packages (from backend.md, present in `.venv`): fastapi==0.115.6,
  uvicorn==0.34.0, python-dotenv==1.0.1, pydantic==2.10.4, PyYAML==6.0.3,
  crewai==0.86.0, litellm==1.95.0, setuptools==79.0.1 (pinned <80 for crewai
  0.86 `pkg_resources` import). `httpx` present for TestClient.
- Test runner: `pytest==9.1.1` installed into `.venv` for this pass (local dev
  dependency only; no secrets, no network, no LLM).
- Safety control: `.env` `OPENAI_API_KEY` is a placeholder value, confirmed
  before running. `run_recommendation` short-circuits with `missing_api_key`
  before any crew build, so no paid LLM call can occur. No real secrets used.
- Test harness: `fastapi.testclient.TestClient` (in-process ASGI); routing and
  same-origin behavior identical to a live Uvicorn server for these checks.

## Smoke Checks (actual results)

### Unit / boundary checks (via pytest TestClient) - `tests/test_smoke.py`

Command: `.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v`
Result: 8 passed in 0.49s. 0 failed.

| # | Check | Expected | Actual | Verdict |
|---|-------|----------|--------|---------|
| 1 | App boots; `GET /health` | 200 `{"status":"ok"}` | 200 `{"status":"ok"}` | PASS |
| 2a | `GET /` serves index.html | 200, references `/static/app.js` + `/static/styles.css` | 200, both references present | PASS |
| 2b | `GET /static/app.js` | 200, contains `/api/recommend` | 200, endpoint present | PASS |
| 2c | `GET /static/styles.css` | 200 | 200 | PASS |
| 3 | `POST /api/recommend` no live key | 503 `missing_api_key` envelope, no shortlist | 503 `{"error":{"code":"missing_api_key","message":...}}`, no `shortlist` key | PASS |
| 4a | `POST /api/recommend` missing `job_requirements` | 422 `detail` | 422, `detail[0].loc=[body,job_requirements]`, `msg="Field required"` | PASS |
| 4b | `POST /api/recommend` `top_n:0` | 422 `detail` | 422, `msg="Input should be greater than or equal to 1"` | PASS |
| 4c | `POST /api/recommend` `top_n:99` | 422 `detail` | 422, `msg="Input should be less than or equal to 25"` | PASS |

Exact envelopes captured (for the frontend contract):

- Missing key (503): `{"error": {"code": "missing_api_key", "message": "OPENAI_API_KEY is not set (or is a placeholder). A valid OpenAI API key is required to run a recommendation. Set it in your .env."}}`. This is the custom `{error:{code,message}}` shape the frontend `handleError` renders.
- Validation (422): FastAPI default `{"detail":[{"loc","msg","type"}]}` shape. Note this is NOT the custom envelope; the integration fix in `src/static/app.js` (`formatValidationDetail`) surfaces this shape as field-level guidance. Confirmed the frontend handles both shapes per integration.md.

### Data sanity - `data/candidates.json` (check 5)

| Item | Expected | Actual | Verdict |
|------|----------|--------|---------|
| Candidate count | ~8-10 synthetic | 10 | PASS |
| Required fields (`id,name,title,years_experience,skills,summary`) | present on all | 0 records missing any field | PASS |
| No real PII | synthetic/fictional | All 10 summaries flagged "Fictional profile"; names clearly invented (e.g. "Ava Testerman", "Rex Samplewood", "Cyrus Notrealson") | PASS |
| Types | skills=list, years=int | all skills lists, all years ints | PASS |

### Crew assembly, no kickoff (check 6)

`build_crew(inputs)` was constructed with placeholder inputs. No `kickoff`, no LLM call.

| Item | Expected (SAD section 2) | Actual | Verdict |
|------|--------------------------|--------|---------|
| Agent count | 3 | 3 | PASS |
| Roles | Researcher, Evaluator, Recommender | Candidate Sourcing Researcher, Candidate Evaluator, Shortlist Recommender | PASS |
| Process | `Process.sequential` | `Process.sequential` | PASS |
| Delegation | all `allow_delegation=false` | `[False, False, False]` | PASS |
| Task count | 3 | 3 | PASS |
| Context chaining | source none, evaluate<-source, recommend<-evaluate | context lengths `[0, 1, 1]` | PASS |
| Memory | `memory=False` | `False` | PASS |
| Controls | `max_rpm` at crew, `max_iter<=12` | `max_rpm=30`, `max_iter=[12,12,12]` | PASS |

## AC Traceability

The PRD does not use explicit AC-* identifiers; it states acceptance criteria as
bullets under Features 1-3 (PRD section 4). QA-derived AC IDs below map to those
bullets. Offline-verifiable vs live-key-required is called out per row.

| AC ID | PRD source | Criterion (summary) | Verifiable offline? | Status this pass |
|-------|-----------|---------------------|---------------------|------------------|
| AC-1.1 | Feature 1 | Valid requirements return a structured candidate list from the synthetic dataset | Partial (dataset loads, crew wired; live output needs key) | PARTIAL - dataset + wiring PASS; live list DEFERRED |
| AC-1.2 | Feature 1 | Missing/ambiguous input does not fail silently (clarify or state assumptions) | Yes (validation path) | PASS - 422 with field-level guidance; empty JR rejected |
| AC-1.3 | Feature 1 | Candidate list passed to Evaluator via context chaining | Yes (assembly) | PASS - context lengths `[0,1,1]` |
| AC-2.1 | Feature 2 | Each candidate scored against criteria | No (needs live LLM) | DEFERRED (needs key) |
| AC-2.2 | Feature 2 | Each score carries supporting evidence/rationale | No (needs live LLM) | DEFERRED (needs key); task `expected_output` schema present |
| AC-2.3 | Feature 2 | Scoring deterministic/reproducible (low temperature) | Partial | PARTIAL - Evaluator/Recommender LLM temp=0.1 configured; reproducibility DEFERRED |
| AC-3.1 | Feature 3 | Ranked shortlist ordered by score | No (needs live LLM) | DEFERRED (needs key); ranking/tie-break in task config + `_normalize_shortlist` |
| AC-3.2 | Feature 3 | Each entry has evidence-based rationale | No (needs live LLM) | DEFERRED (needs key) |
| AC-3.3 | Feature 3 | Per-criterion met/partially_met/missed breakdown | Partial | PARTIAL - schema enforced in tasks.yaml + normalized field; live content DEFERRED |
| AC-3.4 | Feature 3 | Readable ranked format; human keeps final decision | Yes (UI) | PASS - index.html HITL note + results renderer present (frontend.md) |
| AC-NFR-Fail | PRD section 5 | Fail closed: on failure return clear error, no partial shortlist | Yes | PASS - 503 envelope carries no `shortlist`; app boots without key |
| AC-NFR-Sec | PRD section 5 | Synthetic data only, no real PII; secrets via env | Yes | PASS - 10 fictional candidates; key from env, placeholder detected |
| AC-NFR-Empty | PRD section 6 | Empty valid run returns "no strong matches", not error | Partial | PARTIAL - `_normalize_shortlist` sets `notes` default + UI handles empty; live path DEFERRED |

## Defects Found

- None. All executed checks passed. No blocking or non-blocking defects observed
  in the offline surface.

Minor observations (not defects, recorded for completeness):

- Two error shapes coexist by design: custom `{error:{code,message}}` for handled
  failures and FastAPI `{detail:[...]}` for 422. Integration already reconciled the
  frontend to handle both (integration.md). Acceptable for MVP.
- The `RecommendRequest.top_n` is a required-typed field with a default; a
  non-integer or out-of-range value is rejected by Pydantic at 422 before reaching
  the crew layer's own `invalid_input` guard, so the crew-layer `top_n` guard is
  effectively belt-and-suspenders. No functional issue.

## Known Gaps / Future Work

Deferred because they require the operator's `OPENAI_API_KEY` (paid calls) or are
beyond MVP smoke scope:

1. Live end-to-end run: `POST /api/recommend` with a valid key producing a
   non-empty ranked shortlist, validated against the `shortlist` contract
   (`candidate, rank, score, rationale, criteria_breakdown[]`). Covers AC-1.1,
   AC-2.1, AC-2.2, AC-3.1, AC-3.2, AC-3.3 content.
2. Empty "no strong matches" path against live Recommender output (AC-NFR-Empty).
3. Scoring reproducibility: repeat identical inputs and confirm low variance at
   temperature 0.1 (AC-2.3).
4. Runtime failure path with a live key (LLM/crew error -> `runtime_error` 502
   envelope, no partial shortlist).
5. Prompt Trace and per-task lifecycle logs under
   `project-context/2.build/logs` (crewai adapter Logging rule) - not produced
   because no live run occurred.
6. Unit tests for the Recommender tie-break ordering (score desc, then more `met`,
   then stable order) and `_normalize_shortlist` mapping in isolation (SAD section
   9). The logic exists; dedicated unit coverage is recommended.
7. Non-functional: load/concurrency, security assessment (`@security.eng` ->
   `security.md`), and browser-level UI rendering of a live shortlist.

## Overall Smoke Verdict

PASS with scoped gaps.

All 6 requested Tier-0 checks executed with real outcomes and passed (pytest 8/8;
data sanity 4/4 items; crew assembly 8/8 items). The MVP boots, serves the UI,
validates input, fails closed without a key, uses synthetic data only, and
assembles the correct 3-agent sequential crew with context chaining and no
delegation. No defects block the MVP at the offline boundary.

The live-LLM shortlist path (the core value output) is UNVERIFIED here by design
and is the primary residual risk before Deliver. It is recorded as a known gap,
not a failure. Recommendation: run gaps 1-5 with the operator's key, then run a
security assessment (`@security.eng`) before Deliver, since
`aamad.config.example.yml` sets `require_security_assessment: true`.

## Sources

- `project-context/1.define/prd.md` (acceptance criteria, Features 1-3, section 5/6 NFRs).
- `project-context/1.define/sad.md` (sections 2, 4, 9 - crew spec, API contract, testing).
- `project-context/2.build/backend.md`, `frontend.md`, `integration.md` (implementation + prior verification).
- Code executed: `src/app.py`, `src/crew.py`, `src/static/{index.html,app.js,styles.css}`,
  `config/{agents,tasks}.yaml`, `data/candidates.json`.
- `.claude/rules/adapter-crewai.md` (sequential, non-streaming, fail-closed, logging).
- `aamad.config.example.yml` (require_unit_tests, require_security_assessment).
- Test artifact created: `tests/test_smoke.py` (offline, no LLM).

## Assumptions

- The `.env` `OPENAI_API_KEY` is a placeholder; verified before the run so no paid
  call is possible. This is the intended safe path for offline verification.
- `TestClient` (in-process ASGI) is equivalent to a live Uvicorn server for
  routing, static serving, validation, and error-envelope checks.
- The PRD's bullet acceptance criteria are mapped to QA-derived AC IDs for
  traceability; no AC-* identifiers exist in the PRD itself.
- `pytest` installed into `.venv` for this pass is a dev-only dependency; it makes
  no network or LLM calls.
- Default `top_n=5` and bounds 1-25 are the pinned backend behavior (a PRD/SAD Open
  Question); QA validates the implemented behavior, not the deferred final value.

## Open Questions

- What sample job requirements and expected shortlist size define the keyed QA
  acceptance run (gaps 1-2)? (carried from integration.md)
- What scoring-consistency threshold (variance across identical runs) is acceptable
  for AC-2.3? (PRD Open Question)
- Should Prompt Trace and per-task lifecycle logs be persisted under
  `project-context/2.build/logs` during the first keyed run?
- Should dedicated unit tests for tie-break and shortlist normalization be added
  before Deliver, or tracked as follow-up (SAD section 9 calls for them)?

## Audit

- 2026-08-08, qa.eng, qa, resolved runtime crewai. Ran Tier-0 offline smoke via
  FastAPI TestClient in the project `.venv` (Python 3.12.10) with a placeholder
  `OPENAI_API_KEY` (no paid LLM calls). Authored and ran `tests/test_smoke.py`
  (8 passed, 0 failed) covering health, static serving, the 503 missing_api_key
  envelope, and 422 validation. Verified data sanity of `data/candidates.json`
  (10 synthetic candidates, all required fields, no real PII) and crew assembly
  (3 agents, Process.sequential, allow_delegation=false, context chain [0,1,1],
  memory=False, max_rpm=30, max_iter=12). Mapped results to PRD Features 1-3
  acceptance criteria. Overall verdict: PASS with scoped gaps; the live-LLM
  shortlist path is deferred pending the operator's key and recorded as a known
  gap. Installed pytest==9.1.1 into .venv as a dev-only test dependency.
