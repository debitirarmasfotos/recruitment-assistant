# AAMAD MVP System Architecture Document (SAD): Recruitment Assistant

## Context & Instructions

This SAD is the blueprint for the Build-phase personas (backend, frontend, integration, QA) of the Recruitment Assistant MVP. It translates the authoritative PRD (`project-context/1.define/prd.md`) into concrete, implementable architecture decisions so Build agents converge without guessing.

The selected runtime is crewai. Agent and API design align with the CrewAI adapter rule (`.cursor/rules/adapter-crewai.mdc`). Views are intentionally MVP-lean. Nonessential NFRs (formal uptime, horizontal scaling, ATS connectors, persistence) are deferred to Future Work with rationale.

The decisions in this document are approved and pinned. Where the PRD deferred a numeric target, it stays deferred under Open Questions rather than being invented here.

## Input Requirements

**PRD Document**: `project-context/1.define/prd.md` (authoritative)
**MRD** (optional): `project-context/1.define/mrd.md`
**User Stories** (when present): N/A as separate files. User stories are embedded in PRD section 4 (Feature 1, Feature 2, Feature 3).
**MVP Scope**: Core value proposition (80/20). Source, evaluate, and recommend a ranked shortlist with rationale and a per-criterion breakdown, over a synthetic dataset, in a single service.
**Selected Runtime**: crewai

## System Architecture Specification

### 1. MVP Architecture Philosophy & Principles

**MVP Design Principles**:

- Recruiter feedback first: the shortlist output is optimized for scannability and traceability (rank, score, rationale, per-criterion breakdown) so a recruiter can judge value quickly.
- Minimal viable agent set and simplest orchestration: exactly three agents in a CrewAI sequential process, no delegation, no manager agent.
- Observable by default: a `/health` endpoint, per-run `run_id`, and per-task run logging.
- Single-service delivery: one FastAPI process serves both the JSON API and the static UI, so there is no separate frontend host and no CORS surface for the MVP.
- Fail closed, not partial: on any specialist or LLM failure, the run halts and returns a structured error envelope. It never returns a partial or misleading shortlist (PRD section 5, Fault tolerance).

**Core vs Future Features**:

- **MVP**: three-agent crew (Researcher, Evaluator, Recommender); synthetic candidate dataset; `POST /api/recommend`; `GET /health`; static single-page UI; env-based secrets; low-temperature scoring; mandatory human review of the shortlist.
- **Future**: ATS integration, live sourcing connectors (job boards, LinkedIn), candidate communication automation, advanced analytics, persistence of runs, multi-user auth, concurrency/scaling, and formal fairness/compliance controls for automated hiring decisions.
- **Explicit exclusions and deferrals**: no database, no authentication/authorization, no CORS, no streaming, no live external recruiting APIs, no real candidate PII, no numeric SLA. Fairness and hiring-domain regulatory compliance are named as real production concerns and are deferred beyond the MVP, mitigated in the MVP by synthetic data plus mandatory human review.

**Technical Architecture Decisions**:

- Frontend: a minimal single-page static UI built with plain HTML plus vanilla JavaScript, no framework and no build step. Justification: the PRD asks only for a simple input form and a readable ranked-results view (PRD section 6). A framework would add build tooling and dependencies with no MVP value. The UI is served by FastAPI as static files.
- Human-agent interaction: a request/response form, not a chat surface. The recruiter submits job requirements plus optional criteria and receives a rendered ranked shortlist. This matches the batch, non-conversational nature of a single crew run.
- Runtime agent communication: CrewAI sequential process with explicit `Task.context` chaining. Researcher output feeds Evaluator; Evaluator output feeds Recommender.
- Streaming vs non-streaming: non-streaming. `POST /api/recommend` returns a single JSON response after the run completes. Streaming is unnecessary for the MVP and is deferred.

### 2. Multi-Agent System Specification

**Agent Architecture Requirements**:

Three specialized agents, all with `allow_delegation=false`. Definitions are externalized to `config/agents.yaml`; the crew entrypoint lives in code (`src/crew.py`).

- **Researcher** (role: Candidate Sourcing Researcher)
  - Goal: source and compile candidate profiles from the local synthetic dataset that match the provided job requirements.
  - Input: job requirements (and optional criteria) from the request.
  - Data access: reads `data/candidates.json` (synthetic candidates, no real PII).
  - Output: a structured list of candidate profiles, passed to the Evaluator via `Task.context`.

- **Evaluator** (role: Candidate Evaluator)
  - Goal: score each sourced candidate against the job criteria and record per-criterion evidence.
  - Input: the Researcher candidate list plus the criteria, via `Task.context`.
  - Output: per candidate, an overall score plus a per-criterion result of `met` / `partially_met` / `missed` with a short evidence note referencing the candidate profile. Low temperature for scoring determinism.

- **Recommender** (role: Shortlist Recommender)
  - Goal: rank the evaluated candidates and produce a shortlist with per-candidate rationale and the per-criterion breakdown.
  - Input: the Evaluator scored list, via `Task.context`.
  - Output: a ranked shortlist (top_n) where each entry carries rank, score, rationale, and criteria_breakdown.
  - Tie-break (stable and documented, per PRD section 6): order by overall score descending; on effectively equal scores, the candidate with more fully-met (`met`) criteria ranks first; if still tied, preserve the incoming stable order (dataset order). Near-ties are flagged so the recruiter looks closer.

- Memory / session: `memory=False` for reproducibility (adapter Memory rule). No cross-run state.
- Tools / MCP: least privilege. The Researcher reads the local dataset (file read scoped to `data/candidates.json`); Evaluator and Recommender use no external tools. No web or ATS tools in the MVP.

**Task / Turn Orchestration**:

- Execution flow (sequential): Task 1 Source -> Task 2 Evaluate -> Task 3 Recommend. Each task declares the prior task as `context` for deterministic dependency flow.
- Expected outputs and data formats: each task defines `expected_output` describing its structured shape. The final task output maps to the API `shortlist` array. Machine-ingested sections use plain JSON without code fences (adapter Quality Gates).
- Context passing: via `Task.context` only; no shared mutable global state.
- Error handling, retries, cancellation: `max_retry_limit >= 2` for transient LLM errors. If a task still fails, or the LLM is unavailable, the crew run halts and the backend returns the error envelope. No partial shortlist is returned. `max_execution_time` is set per task to bound runaway runs.
- Performance budgets: `max_iter <= 12` per task (adapter baseline); `max_rpm` set at crew level for budget stability; low temperature for the Evaluator scoring task.

**Runtime-Conditional Configuration (crewai)**:

- Crew composition: 3 agents (researcher, evaluator, recommender) and 3 tasks (source, evaluate, recommend).
- Process type: `Process.sequential`.
- YAML config: `config/agents.yaml` (roles, goals, backstories, `allow_delegation=false`, llm/temperature) and `config/tasks.yaml` (descriptions, `expected_output`, `context` chaining, `Task.id`, output expectations). Agents and tasks MUST be externalized to YAML per the adapter Mapping rule.
- Controls: `max_iter <= 12`, `max_retry_limit >= 2`, `max_rpm` at crew level, `max_execution_time` per task, `memory=False`.
- LLM: model resolved from `OPENAI_MODEL` (default `gpt-4o`), key from `OPENAI_API_KEY`, low temperature for scoring.

### 3. Frontend Architecture Specification

**Technology Stack**:

- Framework: none. Plain HTML plus vanilla JavaScript (ES modules or a single script), no build step, no bundler.
- UI library: none. Hand-written minimal markup.
- Styling: a small inline or single `.css` file, minimal styling for readability. Visual style: minimal.
- Type safety / state management: not applicable at MVP scale; a single page with local DOM state.

**Application Structure**:

- Single page served at `/` from `src/static/index.html` (plus optional `src/static/app.js` and `src/static/styles.css`).
- API client boundary: the page calls `POST /api/recommend` via `fetch` on the same origin. No backend logic in the frontend; it only sends the form payload and renders the JSON response.
- Component architecture: one form component (job requirements textarea, optional criteria inputs, top_n input, submit button) and one results component (renders the ranked shortlist). Responsive at a basic level; accessibility baseline via semantic form labels.

**Interface Requirements**:

- Primary interaction surface: a form for job requirements plus criteria, a submit button, and a results area.
- Results rendering: for each shortlisted candidate show rank, candidate identity (synthetic), score, rationale, and the per-criterion breakdown (`met` / `partially_met` / `missed`). Display `run_id` for traceability.
- Loading state: disable submit and show a spinner or "Running..." message while the crew executes.
- Error state: on an error envelope, render the `error.message` clearly and do not render any shortlist rows. Show a "no strong matches" message when the shortlist is empty.
- Future Work placeholders: filtering, saved searches, and export are out of scope for the MVP.

### 4. Backend Architecture Specification

**API Architecture**:

FastAPI service. Two endpoints plus static mount.

- `POST /api/recommend`
  - Request body: `{ "job_requirements": string | object, "criteria"?: [ ... ], "top_n"?: int }`. `job_requirements` is required; `criteria` and `top_n` are optional (server default criteria and a default `top_n` apply when omitted).
  - Success response: `{ "shortlist": [ { "candidate": {...}, "rank": int, "score": number, "rationale": string, "criteria_breakdown": [ { "criterion": string, "result": "met" | "partially_met" | "missed", "evidence": string } ] } ], "run_id": string, "status": "ok" }`.
  - Error response: `{ "error": { "code": string, "message": string } }` with an appropriate HTTP status. On failure the service returns NO partial shortlist.
  - Empty result: a valid run with no strong matches returns `status: "ok"` with an empty `shortlist` and an explanatory field, not an error.
- `GET /health` -> `{ "status": "ok" }`.
- Static files: FastAPI mounts `src/static/` and serves `index.html` at `/`, making the MVP a single service (no CORS needed).
- Validation: reject malformed input (missing `job_requirements`, wrong types, non-positive `top_n`) with the error envelope and guidance (PRD section 6). No rate limiting in the MVP (single-run, deferred).
- Alignment: request/response contracts are fixed here so frontend and integration agents build against the same schema.

**Data Architecture**:

- No database. The only data source is `data/candidates.json`, a small synthetic candidate set loaded at request time (or once at startup) into memory. Persistence of runs and results is deferred to Future Work. Justification: the MVP is single-run and stateless; a store adds no MVP value.

**Runtime Integration Layer**:

- The `POST /api/recommend` handler builds the crew inputs from the request, invokes the CrewAI crew (`src/crew.py`), and maps the Recommender output to the response schema. It generates a `run_id` per request.
- Agent configuration is loaded from `config/agents.yaml` and `config/tasks.yaml`; the crew entrypoint wires agents, tasks, and the sequential process.
- Logging / Prompt Trace: capture rendered prompts (Prompt Trace) and lifecycle events (task start/stop, retries) per adapter Logging rule. Persist run logs under `project-context/2.build/logs` during Build; redact secrets. The API logs `run_id` and per-task completion.

**Authentication & Secrets**:

- Env-var names only, loaded via `python-dotenv`: `OPENAI_API_KEY`, `OPENAI_MODEL`, `AAMAD_TARGET_RUNTIME` (and existing `.env.example` entries `APP_NAME`, `APP_ENV`, `CREWAI_TELEMETRY_OPT_OUT`). No secret values appear in artifacts or committed code. `.env` is gitignored; `.env.example` documents variable names.

### 5. DevOps & Deployment Architecture

- **CI/CD (minimal MVP)**: lint, test (unit plus integration), and build/package. Full pipeline detail is owned by the Deliver phase. No live deploy without operator authorization.
- **Hosting**: smallest MVP-appropriate target: a single containerized FastAPI service (Uvicorn) serving both the API and the static UI. Health check via `GET /health`. Deliver phase pins the exact hosting target, port, and start command.
- **IaC / multi-region / advanced monitoring**: Future Work.
- **Observability**: baseline application logs (per-run `run_id`, per-task events) and the health endpoint. Advanced APM deferred.

### 6. Data Flow & Integration Architecture

- Request/response path: Recruiter fills the form in `index.html` -> browser `fetch` `POST /api/recommend` (same origin) -> FastAPI validates the payload -> handler generates `run_id`, loads `data/candidates.json`, and invokes the CrewAI crew -> Researcher sources candidates -> Evaluator scores them against criteria (via context) -> Recommender ranks and builds the shortlist (via context) -> handler maps output to the response schema -> browser renders the ranked shortlist with per-criterion breakdown.
- External integrations for MVP: only the LLM API (OpenAI) via the CrewAI runtime. No external recruiting APIs.
- Error propagation and user-visible feedback: a validation or runtime failure short-circuits the flow. The handler returns the `{ error: { code, message } }` envelope; the frontend renders the message and shows no partial shortlist. LLM/agent failure halts the run (PRD section 5). An empty-but-valid result surfaces an explicit "no strong matches" message.

### 7. Performance & Scalability Specifications

- Response-time target: complete a run for a modest candidate batch within a reasonable interactive window. The exact numeric target is deferred (PRD Open Questions).
- Concurrency: single-run MVP; no concurrency guarantees. Scaling (batching, caching, ranking heuristics, worker pools) is deferred with rationale: MVP validates value on small synthetic batches first.
- Token / cost controls at the runtime layer: low temperature, small `max_iter`, `max_rpm` at crew level, bounded `top_n`, and a modest dataset size. Cost-per-requisition target is deferred (PRD Open Questions).

### 8. Security & Compliance Architecture

- AuthN/AuthZ: none for the MVP (single-user local/demo service). Deferred to Future Work.
- Secrets: environment variables only via `python-dotenv`; `.env` gitignored; least-privilege LLM API key (PRD section 3, section 5).
- Data protection: synthetic candidate data only in `data/candidates.json`; no real candidate PII is ingested or stored (PRD section 5, MRD section on security).
- Input validation: server-side validation of `job_requirements`, `criteria`, and `top_n`; reject malformed input with guidance. Encryption in transit is a Deliver/hosting concern (TLS at the edge).
- Fairness / compliance: automated hiring decisioning is a regulated, high-scrutiny domain. For the MVP this is mitigated by fixed job-relevant criteria, evidence-based rationale, synthetic data, and mandatory human review of the shortlist (the system recommends and never auto-rejects or contacts candidates). Formal fairness/bias auditing and regulatory compliance are explicitly deferred beyond the MVP and recorded under Open Questions.

### 9. Testing & Quality Assurance Specifications

- Unit tests: request validation (missing/invalid fields), the Recommender ranking and tie-break logic (score desc, then more `met` criteria, then stable order), and the response-mapping layer. `aamad.config` example sets `require_unit_tests: true`.
- Integration tests: `POST /api/recommend` end to end over `data/candidates.json` returning a well-formed shortlist; `GET /health`; the failure path returning the error envelope with no partial shortlist; the empty "no strong matches" path. Tests map to PRD acceptance criteria (Features 1-3).
- Smoke/acceptance: load `/`, submit a sample requirement, and confirm the rendered shortlist shows rank, score, rationale, and per-criterion breakdown.
- Runtime-specific checks: validate `config/agents.yaml` and `config/tasks.yaml` load and that referenced tools resolve before kickoff; confirm sequential `Task.context` chaining; verify machine-ingested output is plain JSON without code fences.
- Security assessment: recommended before Deliver (`aamad.config` example sets `require_security_assessment: true`).

### 10. MVP Launch & Feedback Strategy

- Pilot criteria: a recruiter can go from entering job requirements to a reviewed shortlist in a single session over the synthetic dataset, with visible per-criterion reasoning.
- Success metrics (tied to PRD KPIs, thresholds deferred): time-to-shortlist reduction, shortlist advance rate as the leading recruiter-trust indicator, and scoring consistency/traceability. Technical: run reliability (percentage of valid-input runs completing without error) and reproducibility (low score variance under identical inputs).
- Iteration priorities after first deploy: tune criteria and scoring rubric, expand the synthetic dataset for representativeness, then evaluate live sourcing connectors and persistence.

## Implementation Guidance for AI Development Agents

Intended project layout (Build agents place files here to converge):

```
recruitment-assistant/
  src/
    app.py            # FastAPI app: routes, validation, static mount, crew invocation
    crew.py           # CrewAI crew entrypoint: loads YAML, wires sequential process
    static/
      index.html      # single-page UI served at /
      app.js          # optional: form submit + results rendering
      styles.css      # optional: minimal styling
  config/
    agents.yaml       # researcher, evaluator, recommender (allow_delegation=false)
    tasks.yaml        # source, evaluate, recommend (Task.context chaining, expected_output)
  data/
    candidates.json   # small synthetic candidate set, no real PII
  requirements.txt    # fastapi, uvicorn, crewai, python-dotenv, ...
  .env.example        # variable names only (already present)
```

1. Foundation setup per `setup.md`: create `requirements.txt`, virtualenv, and confirm env vars load.
2. Frontend MVP UI (`src/static/`) without backend wiring: build the form and results renderer against the fixed response schema in section 4.
3. Backend runtime scaffolding per the CrewAI adapter: `config/agents.yaml`, `config/tasks.yaml`, `src/crew.py`, and `src/app.py` with `POST /api/recommend`, `GET /health`, and the static mount.
4. Integration epic wires the frontend fetch call to the backend (same origin, no CORS).
5. QA validates unit, integration, and smoke paths against PRD acceptance criteria.
6. Deliver packages deploy/CI/runbook only.

## Architecture Validation Checklist

- [x] PRD requirements mapped to architectural components (Features 1-3 map to Researcher/Evaluator/Recommender and the recommend endpoint)
- [x] Agents designed for the domain and selected runtime (three-agent sequential CrewAI crew, `allow_delegation=false`)
- [x] Frontend and backend contracts agree on schemas / streaming (shared `POST /api/recommend` JSON contract, non-streaming)
- [x] Secrets via env vars only (`OPENAI_API_KEY`, `OPENAI_MODEL`, `AAMAD_TARGET_RUNTIME`)
- [x] MVP vs Future Work boundaries explicit
- [x] Resolved `AAMAD_TARGET_RUNTIME` recorded in Audit

## Sources

- `project-context/1.define/prd.md` (authoritative PRD; sections 3, 4, 5, 6, 7, 8)
- `project-context/1.define/mrd.md` (Recruitment Assistant MRD)
- `.cursor/rules/adapter-crewai.mdc` (CrewAI adapter rules)
- `.cursor/templates/sad-template.md` (structure and headings)
- `.env.example` and `aamad.config.example.yml` (env var names and project preferences)

## Assumptions

- No `aamad.config.yml` exists at the project root; only `aamad.config.example.yml` is present. Its preferences (Python primary, security assessment required, unit and integration tests required, minimal UI) are treated as guidance, and `AAMAD_TARGET_RUNTIME=crewai` is authoritative for runtime.
- `data/candidates.json` does not yet exist; the Build phase creates the synthetic dataset. Its exact structure and size are deferred (PRD Open Questions) but each record is synthetic with no real PII.
- The MVP is a single-user demo service; no authentication is required.
- Default criteria and a default `top_n` are applied server-side when the request omits them; the specific default rubric is owned by the Evaluator task config and pending criteria approval.
- Same-origin static serving removes the need for CORS in the MVP.
- Model defaults to `gpt-4o` (from `.env.example` `OPENAI_MODEL`) unless overridden.

## Open Questions

- Which specific job-relevant criteria and scoring rubric should the Evaluator use, and who approves them? (PRD)
- What is the acceptable maximum run time for a modest candidate batch, and the target cost per requisition? (PRD)
- What structure and size should `data/candidates.json` have to be representative? (PRD)
- What default `top_n` should the shortlist use when the request omits it?
- What scoring consistency threshold (variance across identical runs) is acceptable? (PRD)
- Beyond synthetic-data plus human review, what fairness/bias auditing and regulatory controls are required before any non-MVP hiring use?

## Audit

- 2026-08-08, system.arch, create-sad, resolved runtime crewai
