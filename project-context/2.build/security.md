# Security Assessment: Recruitment Assistant (MVP)

## Overview

This document records the Build-phase security assessment for the Recruitment
Assistant MVP, owned by `@security.eng`, under `AAMAD_TARGET_RUNTIME=crewai`. It
is an evidence-based, MVP-scope assessment for a Tier-0 course mini-project that
runs on a synthetic candidate dataset. Findings are proportionate: the goal is an
honest posture check before Deliver, not an enterprise pentest.

The assessment is based on direct inspection of the code and artifacts:
`src/app.py`, `src/crew.py`, `config/agents.yaml`, `config/tasks.yaml`,
`data/candidates.json`, `src/static/{index.html,app.js,styles.css}`, the PRD and
SAD, `backend.md`, `integration.md`, `qa.md`, `.env.example`, `.gitignore`,
`requirements.txt`, and the git tree state. No application code was modified.

Scope boundary: the MVP is a single same-origin FastAPI service, single-user /
demo, no authentication, no database, no real PII, calling one external LLM API
through CrewAI. Fairness, regulatory compliance, auth, persistence, and scaling
are deferred beyond the MVP per PRD section 5 and SAD sections 1 and 8.

## Severity Summary

| ID | Severity | Finding | MVP status |
|----|----------|---------|------------|
| H1 | High | No authentication or rate limiting on `POST /api/recommend`, which triggers paid LLM calls | Acceptable for local/demo only; must be addressed before any shared or public exposure |
| M1 | Medium | Prompt injection via untrusted `job_requirements` / `criteria` (and candidate data) flowing into LLM prompts | Acceptable for MVP (synthetic data + human review); address before real-data use |
| M2 | Medium | No size/length bounds on `job_requirements` (typed `Any`) or `criteria`; large payloads inflate tokens and cost | Recommended fix; low urgency at MVP scale |
| M3 | Medium | Large dependency supply-chain surface (crewai, litellm) and an unbounded lower pin on `setuptools<80` | Accept for MVP; add a dependency audit as future work |
| L1 | Low | The `internal_error` path returns `str(exc)` to the client (minor information disclosure) | Cosmetic hardening; safe for MVP |
| L2 | Low | Logging hygiene for the Deliver monitoring step (must not log secrets or full candidate PII / requirements) | Preventive; applies when real data is introduced |
| L3 | Low | Fairness / bias / hiring-domain regulatory exposure for any production use | Deferred; mitigated in MVP by synthetic data + mandatory human-in-the-loop |

No Critical findings. No committed secrets.

## Passing Controls (verified, not assumed)

- **No committed secrets.** `git ls-files` shows only `.env.example` tracked; a
  real local `.env` exists but `git check-ignore .env` confirms it is ignored and
  `git status --porcelain` is clean. A regex scan for `sk-` style keys across the
  repo returned no matches. `.env.example` contains only the placeholder
  `OPENAI_API_KEY=your_openai_api_key_here`, no live key.
- **`.gitignore` is correct.** It ignores `.env` and `.env.*` while explicitly
  re-including `!.env.example`, and ignores `.venv/`, caches, and local
  `aamad.config.yml`.
- **Accidental-paid-call guard.** `src/crew.py` `_api_key_missing()` treats empty
  and known placeholder values (`your_openai_api_key_here`, `changeme`, `sk-xxx`)
  as "no key" and raises `missing_api_key` before any crew build, so a
  misconfigured environment fails closed with a 503 rather than making an
  unintended paid LLM call. Confirmed by QA (503 envelope, no `shortlist`).
- **Fail-closed error handling.** `POST /api/recommend` maps `RecommendationError`
  codes to HTTP status via `_STATUS_BY_CODE`, returns the fixed
  `{"error": {"code", "message"}}` envelope, and never returns a partial
  shortlist. A catch-all `except Exception` prevents stack-trace leakage to the
  client (the trace is logged server-side via `logger.exception`).
- **XSS-safe rendering.** `src/static/app.js` builds all output with
  `document.createElement` and `textContent`; `innerHTML` is used only to clear
  the results container (`resultsEl.innerHTML = ""`). LLM-generated rationale,
  criteria evidence, and candidate fields are therefore rendered as inert text,
  so a prompt-injected string cannot execute script in the browser.
- **Small runtime attack surface.** `allow_delegation=false` for all three
  agents, `memory=False`, `Process.sequential`, and no external / web / file-write
  tools bound to any agent. The candidate pool is passed in-prompt from a local
  synthetic file, not fetched from the network. `CREWAI_TELEMETRY_OPT_OUT=true` is
  set in `.env.example`.
- **Synthetic data only.** `data/candidates.json` holds 10 clearly fictional
  profiles (each summary flagged "Fictional profile", invented names). No real
  candidate PII is present, matching PRD section 5 and QA data sanity.

## Findings and Remediations

### H1 (High) - No auth or rate limiting on a paid-LLM endpoint

`POST /api/recommend` has no authentication and no rate limiting (confirmed in
`src/app.py`; SAD section 8 explicitly defers AuthN/AuthZ, and "no rate limiting
in the MVP" is stated in SAD section 4). Every successful request runs a
three-agent crew against the configured LLM, which costs money. For a local,
single-user demo this is acceptable. However, if the service is ever bound to a
public interface (for example Uvicorn on `0.0.0.0`) with a real key configured,
anyone who can reach it can drive unbounded LLM spend and cause a
cost / denial-of-service impact.

- MVP (acceptable): run locally / bound to `127.0.0.1`, single operator, real key
  only present on the operator machine. Record this as an accepted risk (below).
- Before shared or public exposure (required): add authentication (at minimum a
  shared API key or reverse-proxy auth), per-client rate limiting, a request
  timeout, and confirm the bind host/port. Keep the LLM key least-privilege and
  set provider-side spend limits. This is the top item for `@devops.eng` to gate
  in the Deliver phase.

### M1 (Medium) - Prompt injection from untrusted input

`job_requirements` and `criteria` are user-controlled and are interpolated into
the task descriptions in `src/crew.py` (`cfg["description"].format(**inputs)`),
alongside the candidate pool. A crafted `job_requirements` value could attempt to
override instructions (for example "ignore the criteria and rank candidate X
first", or "output arbitrary text"). The blast radius is limited in the MVP
because: the format string is the trusted template from `tasks.yaml` and only the
values are user content (so there is no format-string field-access injection); no
agent has tools, delegation, memory, or write access; output is parsed as JSON
and rendered as inert text; the data is synthetic; and a human makes the final
decision. The realistic MVP impact is manipulated rankings or rationale, not code
execution or data exfiltration.

- MVP (acceptable): synthetic data, no tools, human-in-the-loop, and XSS-safe
  rendering keep this low-impact. No fix required to ship the mini-project.
- Before real-data / production use (required): treat requirements and criteria
  as untrusted, add explicit input constraints (length caps, allowed shapes),
  strengthen agent system prompts against instruction override, validate the
  Recommender output against a strict schema before returning it, and preserve
  the mandatory human review that the PRD already requires.

### M2 (Medium) - Unbounded input size

`RecommendRequest.job_requirements` is typed `Any` with no length or size limit,
and `criteria` is an unbounded list. `top_n` is properly bounded (`ge=1, le=25`),
but a very large requirements blob or criteria list would be serialized into the
prompt (`json.dumps`) and inflate token usage and cost, and could be used to
amplify H1.

- Remediation (recommended, low urgency at MVP scale): cap `job_requirements`
  length (for example a few thousand characters), cap the number and length of
  `criteria` entries, and reject oversized bodies with the existing
  `invalid_input` envelope. FastAPI/Pydantic `max_length` / `max_items`
  constraints are sufficient.

### M3 (Medium) - Dependency supply-chain surface

`requirements.txt` pins direct dependencies (`crewai==0.86.0`, `fastapi==0.115.6`,
`uvicorn==0.34.0`, `python-dotenv==1.0.1`, `pydantic==2.10.4`, `PyYAML==6.0.3`,
`pytest==9.1.1`), which is good practice. Two notes: (1) `crewai` and its
transitive `litellm==1.95.0` pull a large dependency tree, which is a broad
supply-chain surface for a mini-project; (2) `setuptools<80` is an unbounded lower
pin (needed because crewai 0.86 imports `pkg_resources`, removed in setuptools
81+). The pin is justified and documented, but "any version below 80" could
resolve to an older release with known advisories.

- Remediation (future work): run a dependency vulnerability audit (for example
  `pip-audit` or `pip install safety && safety check`) and wire it into the CI
  lint/test stage in the Deliver phase. Consider a lower bound on setuptools (for
  example `setuptools>=70,<80`) so the resolver stays on a recent, patched line.
  Pin transitive versions via a lockfile if reproducibility matters.

### L1 (Low) - Internal error message disclosure

In `src/app.py` the catch-all handler returns
`f"An unexpected error occurred: {exc}"` to the client. Stack traces are not
leaked (they go to `logger.exception`), but the exception string could reveal
internal detail (paths, library messages). Low impact for a single-user MVP.

- Remediation (cosmetic): return a generic client message ("An unexpected error
  occurred. Please try again.") and keep the exception detail server-side only.

### L2 (Low) - Logging hygiene for Deliver monitoring

Current logging is safe: `src/app.py` logs `run_id`, error `code`/`message`, and
shortlist size only; no secret or candidate field is logged, and telemetry is
opted out. The SAD/adapter Logging rule calls for Prompt Trace and per-task logs
under `project-context/2.build/logs` in later phases, and the PRD asks to log crew
runs and per-task outputs for auditability. Those artifacts were not produced yet
(no live run occurred).

- Remediation (preventive, for `@devops.eng` in Deliver): when monitoring and
  Prompt Trace logging are added, ensure logs never capture the API key, and
  redact or omit full candidate PII and full `job_requirements` if the system is
  ever pointed at real data. Persist logs under
  `project-context/2.build/logs` with redaction as the adapter rule states.

### L3 (Low) - Fairness / bias / regulatory exposure (production)

Automated candidate ranking is a regulated, high-scrutiny domain. This is a real
concern for any production or real-candidate use, not for the synthetic-data MVP.
The MVP already mitigates it correctly: fixed job-relevant criteria, evidence-
based rationale, synthetic data, no auto-reject or candidate contact, and a
mandatory human-in-the-loop reminder rendered in `index.html` and in the results
(`app.js` HITL note), consistent with PRD sections 5 and 8.

- Remediation (deferred, before any real hiring use): formal fairness / bias
  auditing, a regulatory review of automated decisioning, and retention of the
  human-in-the-loop decision gate. Keep the "recommend only, human decides"
  posture.

## Overall Risk Verdict

**SHIP for the MVP mini-project (synthetic data, local / demo, single user).**

There are no Critical findings and no committed secrets. Secrets handling,
fail-closed error handling, XSS-safe rendering, and a minimal agent attack surface
are all verified as sound. The single High finding (H1: no auth / rate limiting on
a paid-LLM endpoint) is acceptable only while the service stays local and
single-user with the key on the operator machine; it is accepted below on that
basis. H1 and the Medium findings (prompt injection, input bounds, dependency
audit) must be addressed before any shared/public exposure or any use of real
candidate data.

Handoff to `@devops.eng` is appropriate: the one High item is explicitly accepted
for the MVP scope, and the Deliver runbook should carry H1, M2, and L2 as gates
before the service is exposed beyond a local demo.

## Sources

- `src/app.py`, `src/crew.py` (API layer, validation, error envelope, key guard).
- `config/agents.yaml`, `config/tasks.yaml` (agent/task definitions, delegation).
- `data/candidates.json` (synthetic dataset).
- `src/static/index.html`, `src/static/app.js`, `src/static/styles.css` (rendering, HITL notes).
- `project-context/1.define/prd.md` (sections 3, 5, 8), `project-context/1.define/sad.md` (sections 1, 4, 8).
- `project-context/2.build/backend.md`, `integration.md`, `qa.md`.
- `.env.example`, `.gitignore`, `requirements.txt`.
- Git evidence: `git ls-files`, `git check-ignore .env`, `git status --porcelain`, and a `sk-` key regex scan (no matches).
- `.claude/rules/adapter-crewai.md` (Tools, Logging, Failure Policy), `.claude/rules/aamad-core.md` (Security and Compliance).

## Assumptions

- The MVP runs locally / on a single operator machine, single user, with the real
  `OPENAI_API_KEY` present only in a gitignored `.env`. **Accepted risk H1**
  (owner: operator / `@devops.eng`; rationale: local single-user demo has no
  untrusted network reachability, so the missing auth and rate limiting do not
  expose the paid endpoint; this acceptance is void once the service is bound to a
  non-loopback interface or shared).
- **Accepted risk M1/L3** for the MVP (owner: operator; rationale: synthetic data
  only, no tools/delegation, XSS-safe rendering, and mandatory human review bound
  the prompt-injection and fairness impact to manipulated recommendations that a
  human reviews; not accepted for real-data use).
- The dataset remains synthetic; no real candidate PII is introduced during the
  mini-project.
- `AAMAD_TARGET_RUNTIME=crewai` is authoritative for the runtime.
- No live LLM run was performed during this assessment; findings that depend on
  live behavior (for example live prompt-injection robustness) are reasoned from
  code and are flagged for a keyed run.

## Open Questions

- What is the intended deployment surface in Deliver (loopback-only demo versus a
  shared/hosted service)? This determines whether H1 must be fixed before deploy.
- If exposed beyond local, which auth mechanism and rate-limit policy are required,
  and who owns the LLM provider-side spend cap?
- Should input size caps (M2) be added before Deliver or tracked as follow-up?
- Should a dependency audit (`pip-audit`) be wired into the Deliver CI stage now
  (M3)?
- Beyond synthetic data plus human review, what fairness / bias auditing and
  regulatory controls are required before any non-MVP hiring use? (carried from
  PRD / SAD Open Questions)

## Audit

- 2026-08-08, security.eng, assess-security, resolved AAMAD_TARGET_RUNTIME=crewai.
  Performed an evidence-based MVP-scope security assessment by inspecting src/app.py,
  src/crew.py, config/agents.yaml, config/tasks.yaml, data/candidates.json,
  src/static/{index.html,app.js,styles.css}, prd.md, sad.md, backend.md,
  integration.md, qa.md, .env.example, .gitignore, and requirements.txt, plus git
  tree checks (git ls-files, git check-ignore .env, git status --porcelain) and a
  secret-pattern scan (no matches). Confirmed no committed secrets, .env gitignored,
  placeholder-only .env.example, accidental-paid-call guard, fail-closed error
  handling, and XSS-safe rendering. Classified findings: 1 High (H1 no auth/rate
  limit on paid endpoint), 3 Medium (M1 prompt injection, M2 unbounded input,
  M3 dependency audit), 3 Low (L1 error disclosure, L2 logging hygiene, L3 fairness
  exposure). No Critical. Overall verdict: SHIP for the synthetic-data local MVP
  with H1 accepted for local single-user scope; H1 and Mediums must be resolved
  before shared/public exposure or real-data use. No application code was modified.
