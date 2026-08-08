# Execution Results

## Test Run: 2026-08-08

End-to-end run of the deployed Recruitment Assistant using the documented local
runbook (`main.py` via uvicorn), exercising the running HTTP service. The paid
LLM path (a live ranked shortlist) was not run here because it requires a real
`OPENAI_API_KEY`; that is a scoped, documented gap, not a defect. Everything that
does not require a paid key was executed against the real running server and the
actual responses are captured verbatim below.

### Environment
- Host / port: `127.0.0.1:8123` (local loopback, per the security assessment).
- Runtime: `AAMAD_TARGET_RUNTIME=crewai`; model `gpt-4o`; `APP_ENV=production`.
- API key: not set (placeholder). Logged as `api_key_present=False` (boolean only, key never logged).
- Launch command: `APP_HOST=127.0.0.1 APP_PORT=8123 APP_ENV=production python main.py`

### Execution timeline
- Server startup: application startup completed; uvicorn served on `http://127.0.0.1:8123`.
- Startup log line emitted (stdout + `logs/app.log`):
  `startup: app=Recruitment Assistant version=0.1.0 env=production runtime=crewai model=gpt-4o api_key_present=False`

### Requests exercised (actual responses)

1. `GET /health`
   - Response: `{"status":"ok"}`
   - Result: HTTP 200 in ~0.018s. PASS.

2. Static UI served
   - `GET /` -> HTTP 200, 3805 bytes (index.html).
   - `GET /static/app.js` -> HTTP 200.
   - `GET /static/styles.css` -> HTTP 200.
   - Result: the single-service same-origin UI is served correctly. PASS.

3. `POST /api/recommend` (happy-path shape, no live key)
   - Body: `{"job_requirements":"Senior Python engineer, 5+ years, FastAPI and cloud, strong testing","criteria":["Python","FastAPI","Cloud","Testing"],"top_n":3}`
   - Response: `{"error":{"code":"missing_api_key","message":"OPENAI_API_KEY is not set (or is a placeholder). A valid OpenAI API key is required to run a recommendation. Set it in your .env."}}`
   - Result: HTTP 503 in ~0.004s. Fail-closed as designed: a clear error, no partial shortlist, no crash. PASS (contract/boundary verified; live scoring deferred to the key-enabled run).

4. `POST /api/recommend` (invalid input, `top_n=0`)
   - Response: `{"detail":[{"type":"greater_than_equal","loc":["body","top_n"],"msg":"Input should be greater than or equal to 1","input":0,"ctx":{"ge":1}}]}`
   - Result: HTTP 422. Input validation works and returns the shape the frontend renders. PASS.

### Application Crew execution
- Crew assembly was verified in QA (`project-context/2.build/qa.md`): 3 agents
  (Researcher, Evaluator, Recommender), `Process.sequential`, `allow_delegation=false`
  for all, context chain lengths `[0,1,1]`, `memory=False`. Built without an LLM call.
- Researcher / Evaluator / Recommender live stage output: NOT executed here (requires
  a valid `OPENAI_API_KEY`; `crew.kickoff()` would incur paid LLM calls).

### Output
- Live ranked shortlist output: not produced in this run (no key). The response
  contract that will carry it is verified: on success the endpoint returns
  `{ shortlist: [ { candidate, rank, score, rationale, criteria_breakdown } ], run_id, status }`.
- To produce a live shortlist: set a real `OPENAI_API_KEY` in `.env`, restart, and
  repeat request 3 above; the crew will source, evaluate, and recommend over
  `data/candidates.json`.

### Logs / Traces
- Logs written to stdout and `logs/app.log` (gitignored). Observed lines: startup,
  request `received` (with run_id and a bounded `job_requirements` summary, no full
  text or PII), and terminal `failed` line on the 503 path with run_id, status, and
  `duration_ms`.
- CrewAI tracing: available behind `CREWAI_TRACING_ENABLED=true` plus `crewai login`;
  not enabled in this run (no network/auth calls). See deploy.md Monitoring and
  Observability for the setup and `app.crewai.com -> Traces` viewing steps.

### Issues Encountered
- None for the offline surface. The only non-executed path is the live LLM
  recommendation, which is intentionally gated on the operator's API key.

### Observations
- What worked well: the deployed service boots cleanly from `main.py`, serves the UI
  and API on one origin, logs with run_id correlation and PII/secret redaction,
  validates input, and fails closed without a key rather than crashing or returning a
  partial result.
- What to do next: run the key-enabled path to capture a real ranked shortlist and
  validate the live Recommender JSON against the `shortlist` contract, then review a
  CrewAI trace for the three-stage timeline.

## Sources
- `project-context/3.deliver/deploy.md` (runbook followed for this run)
- `project-context/2.build/qa.md` (crew assembly and smoke results)
- `project-context/2.build/security.md` (loopback bind and no-key guard rationale)
- Live server output and curl responses captured 2026-08-08

## Assumptions
- Local single-user run on loopback; no real candidate data (synthetic dataset only).
- A valid `OPENAI_API_KEY` is required for the live recommendation path and was not used here.

## Open Questions
- Live end-to-end shortlist quality, scoring reproducibility at low temperature, and
  cost per requisition: to be measured once a real key is supplied.

## Audit
- 2026-08-08, devops-eng (operator execution), run-application, resolved AAMAD_TARGET_RUNTIME=crewai. Offline-surface end-to-end run PASS; live LLM path deferred to a key-enabled run.
