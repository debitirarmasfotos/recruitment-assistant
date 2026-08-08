# Frontend Implementation: Recruitment Assistant (MVP)

## Overview

This document records the Build-phase frontend implementation for the Recruitment
Assistant MVP, owned by `@frontend.eng`. It implements the minimal single-page UI
pinned in `project-context/1.define/sad.md` section 3: plain HTML plus vanilla
JavaScript, no framework, no build step, served by FastAPI as static files on the
same origin (no CORS).

Scope is MVP-lean and UI-only. The frontend does not connect to or contain backend
logic; it sends the request payload to the existing `POST /api/recommend` endpoint
and renders the JSON response. Backend wiring beyond the same-origin fetch call is
the Integration epic's concern.

## What Was Built

Files created / changed (all under `src/static/`):

- `index.html` (replaced the backend placeholder) - the recruiter form and the
  results container. Semantic form labels, a human-in-the-loop (HITL) note, and a
  disabled Future Work placeholder row (filter, save search, export).
- `app.js` (new) - form handling, payload construction, the `fetch` call to
  `POST /api/recommend`, and the results/error/empty renderer. Vanilla ES5-style
  JS in an IIFE, no dependencies, no modules to keep it framework-free and
  build-free.
- `styles.css` (new) - minimal styling using system fonts, readable spacing, and
  basic responsiveness. No external CDNs or fonts.

### The form (recruiter input)

- `job_requirements`: a required textarea (role, key skills, must-haves).
- `criteria`: an optional textarea. The user types one criterion per line or
  separates by commas; `app.js` splits on newlines/commas, trims, and drops empty
  entries into a string array. Omitted when blank so the server applies its
  default behavior.
- `top_n`: a number input, default 5, min 1, max 25 (matches the backend
  `Field(default=5, ge=1, le=25)`).
- Submit button labeled "Find candidates".

### Results rendering (scannable ranked shortlist)

For each shortlist entry the UI renders, per PRD section 6 and SAD section 3:

- rank (`#N` badge, from `entry.rank`, falling back to list order),
- candidate identity (`candidate.name` and `candidate.title`, with graceful
  fallbacks to `id`/`role`/"Candidate N"),
- overall score (`entry.score`),
- rationale (`entry.rationale`),
- per-criterion breakdown (`entry.criteria_breakdown[]`): each `criterion` with a
  color-coded badge for `result` (`met` / `partially_met` / `missed`, plus an
  `unknown` fallback) and the `evidence` note.

The response `run_id` is displayed for traceability and any `notes` field is shown.
A results-area reminder restates that final hiring decisions remain with a human.

## Mapping to the Backend API Contract

Field names match the backend contract exactly (`project-context/2.build/backend.md`,
`sad.md` section 4). Verified against the running app, not just read.

- Request sent: `{ job_requirements: string, criteria?: string[], top_n?: number }`
  to `POST /api/recommend` with `Content-Type: application/json`, same origin.
- Success shape consumed: `{ shortlist: [ { candidate, rank, score, rationale,
  criteria_breakdown: [ { criterion, result, evidence } ] } ], run_id, status, notes? }`.
- `candidate` object fields consumed: `name`, `title` (from `data/candidates.json`
  shape `{ id, name, title, years_experience, skills, summary }`), with fallbacks.
- Error shape consumed: `{ error: { code, message } }`.

## States Handled (honest, no silent failures)

- Loading: submit button disabled and a "Running the crew..." status line shown
  while the request is in flight; cleared on completion. This aligns with the
  non-streaming contract (SAD section 1): a single response after the run
  completes, so a simple busy indicator is correct and no streaming UI is implied.
- Success with results: renders the ranked shortlist as described above.
- Success with empty shortlist: when `status: "ok"` and `shortlist` is empty, shows
  a "No strong matches" message using the server `notes` when present, not an error.
- Error envelope: on any non-OK response or a body containing `error`, renders
  `error.message` and `error.code` clearly (for example 503 `missing_api_key`,
  422 validation) and renders no shortlist rows. A network/fetch failure shows a
  distinct "Network error" message.
- Client-side guard: an empty `job_requirements` is caught before the request and
  the user is told it is required (the server also validates; this is a friendly
  early check, not a replacement).

## Verification (done without a live LLM key, no paid calls)

Booted the FastAPI app via `fastapi.testclient.TestClient` using the existing
project virtualenv and confirmed:

- `GET /` -> 200, serves `index.html` and references `/static/app.js` and
  `/static/styles.css`.
- `GET /static/app.js` -> 200; contains the correct endpoint `/api/recommend` and
  the contract field names (`job_requirements`, `criteria_breakdown`).
- `GET /static/styles.css` -> 200.
- `GET /health` -> 200 `{"status": "ok"}`.
- `POST /api/recommend` with no key -> 503 `{"error": {"code": "missing_api_key",
  ...}}`, confirming the error-envelope path the UI renders. No paid LLM call.
- `POST /api/recommend` with `top_n: 0` -> 422, confirming the validation-error path.

Not verified (requires the operator's `OPENAI_API_KEY` and would incur paid LLM
calls; deferred to QA/integration): rendering a real non-empty shortlist and the
empty "no strong matches" path against live Recommender output. The renderer was
written defensively (fallbacks for missing fields) so shape drift degrades
gracefully rather than crashing.

## Traceability Notes (runtime-driven UI constraints)

- Non-streaming runtime (SAD section 1, crewai sequential process): the UI uses a
  single request/response with a busy indicator, not incremental streaming. If a
  future runtime introduces streaming, the loading state would need to become a
  progressive renderer. Recorded here so the constraint is traceable.
- Single-service, same-origin serving removes CORS from the MVP; the fetch call
  uses a relative path (`/api/recommend`) and no cross-origin headers.

## Sources

- `project-context/1.define/prd.md` (authoritative PRD; sections 4, 6 - ranked
  shortlist, per-criterion breakdown, HITL, empty/error states).
- `project-context/1.define/sad.md` (pinned architecture; section 3 Frontend, section
  4 API contract, section 6 data flow).
- `project-context/2.build/backend.md` (the API contract and field names this UI
  calls, plus the error-code/HTTP-status mapping).
- `src/app.py`, `data/candidates.json` (static serving behavior and candidate shape).

## Assumptions

- The `candidate` object exposes `name` and `title` (per `data/candidates.json`);
  the renderer falls back to `id`/`role`/"Candidate N" if a field is absent, because
  the exact live Recommender JSON was not exercised without a key.
- `criteria` is sent as a string array parsed from newline/comma-separated input;
  the backend accepts an optional list and infers defaults when omitted.
- `top_n` default 5 and bounds 1-25 mirror the backend Pydantic field; this remains
  a SAD/PRD Open Question but the UI simply follows the backend default.
- Score is rendered as-is (`Score <value>`); the backend describes 0-100 scoring but
  the UI does not assume a fixed scale in case the range changes.

## Open Questions

- Should the candidate card also surface `skills`, `years_experience`, or `summary`
  from the profile, or keep the card lean (name, title, score, rationale, breakdown)?
  Kept lean for the MVP to stay scannable; easy to extend.
- Should near-tie flagging (PRD section 6, SAD section 2) get a distinct visual
  marker, or is the rationale text sufficient? Currently it relies on the
  Recommender's rationale prose; no dedicated UI flag was added.
- Exact score scale/format to display (0-100 assumed by backend, not enforced in UI).

## Audit

- 2026-08-08, frontend.eng, develop-fe, resolved runtime crewai. Replaced
  `src/static/index.html` and added `src/static/app.js` and `src/static/styles.css`:
  a minimal no-framework, no-build recruiter form (job_requirements, criteria, top_n
  default 5) posting to `POST /api/recommend` same-origin, and a scannable ranked
  results renderer showing rank, name/title, score, rationale, and the per-criterion
  met/partially_met/missed breakdown with evidence. Handled loading, success, empty
  ("no strong matches"), and error-envelope states, plus a HITL human-review note.
  Verified via TestClient with no paid LLM calls: GET / and both static assets 200;
  GET /health 200; POST /api/recommend surfaces 503 missing_api_key and 422 validation
  envelopes that the UI renders. Full non-empty shortlist rendering deferred pending
  OPENAI_API_KEY.
