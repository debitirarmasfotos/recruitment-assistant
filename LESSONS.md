# Lessons Learned

Reflection on building the Recruitment Assistant end to end with the AAMAD
framework, across Define, Build, and Deliver. Runtime target:
`AAMAD_TARGET_RUNTIME=crewai`.

## Define Phase

What worked:
- Starting with the MRD and PRD forced the problem and success metrics to be
  settled before any code existed, so the Build agents implemented a decided
  product instead of improvising one.
- `@product-mgr` produced structured, template-conformant artifacts with the
  Sources / Assumptions / Open Questions / Audit footers, which made provenance
  and traceability automatic rather than an afterthought.
- Keeping unknowns as explicit Open Questions (numeric thresholds, the scoring
  rubric owner, dataset size) was more honest than inventing statistics, and it
  gave later phases a clear list of what still needed a decision.

What I would change:
- Decide the evaluation criteria / scoring rubric earlier. It stayed an Open
  Question into Build, which is the one place the Evaluator agent most needed a
  concrete contract.
- Pin at least a directional target for the headline metrics (time-to-shortlist,
  shortlist advance rate) so success is measurable, not just defined.

How `@product-mgr` helped:
- It behaved as a single-responsibility persona: it based the PRD on the MRD,
  followed the templates, stayed in Define scope, and did not wander into
  architecture. That focus is what kept the output consistent and reviewable.

## Build Phase

Multi-persona orchestration:
- Running each persona (`@system.arch`, `@backend.eng`, `@frontend.eng`,
  `@integration.eng`, `@qa.eng`) in its own step with fresh context kept each one
  focused and prevented role bleed. Each consumed the prior artifacts and produced
  its own, which is exactly how a real team hands off.
- Pinning the cross-cutting decisions up front (single FastAPI service serving the
  static UI, the `/api/recommend` contract, synthetic-data-only) meant the
  independent agents converged instead of each inventing a different interface.

Canonical artifacts:
- `backend.md`, `frontend.md`, `integration.md`, and `qa.md` were the interface
  between steps. Because the contract lived in files, the integration and QA steps
  could pick up work without replaying any earlier conversation.

Challenges:
- A real dependency issue surfaced: crewai 0.86 imports `pkg_resources`, removed in
  setuptools 81+, so `setuptools<80` had to be pinned. Worth remembering that
  agent-framework installs carry sharp edges.
- Frontend and backend drifted on one error shape (FastAPI returns 422 as
  `{detail}`, not the custom `{error}` envelope). Integration caught and fixed it.
  That is the value of a distinct integration step rather than assuming the pieces
  fit.
- The live LLM path could not be exercised without a paid key, so verification was
  scoped to everything that does not need one (health, static serving, validation,
  crew assembly, smoke tests). Being explicit about that gap kept QA honest.

## Deliver Phase

Deployment challenges:
- Docker was not available in this environment, so the Dockerfile and compose stack
  are provided but were not built here. The local `main.py` path was run for real.
- Binding to loopback by default (`127.0.0.1`) came directly from the security
  assessment (no auth or rate limiting yet), a good example of a Build/Deliver
  artifact changing a concrete default.

Usefulness of `deploy.md`:
- Consolidating hosting, the env-var matrix (names only, no secrets), start/stop/
  rollback, access control, monitoring, and troubleshooting into one runbook means
  someone new could operate the app without reading the code. The end-to-end run in
  `execution-results.md` was done by following that runbook.

Observability:
- Adding structured logging with run_id correlation and secret/PII redaction, plus
  CrewAI tracing behind a default-off env flag, gave visibility without leaking
  data and without forcing network/auth on local runs.

## AAMAD Framework

Most valuable features:
- The Define -> Build -> Deliver spine with single-responsibility personas and
  canonical artifacts. It turns "prompt an AI to build something" into a repeatable,
  auditable process with clean handoffs.
- The templates and `aamad validate` quality gates. Validation caught a real issue
  (the Audit sections needed the literal `AAMAD_TARGET_RUNTIME=crewai` token), which
  is exactly the kind of consistency a human reviewer would miss.
- Runtime adapters: `AAMAD_TARGET_RUNTIME` shaped the generated app (CrewAI YAML
  agents/tasks, sequential process) without changing the methodology.

Gaps vs the full CHECKLIST:
- This was a Tier-0 path: `setup.md` was folded into the env step, QA was a smoke
  pass rather than full unit + integration with AC-* traceability, and the live LLM
  end-to-end run was deferred. A full project would close those.

## Agentic Architect Role

Balancing the three hats:
- Business and Experience hats came most naturally and drove real changes in Define:
  adding the per-criterion breakdown (Experience) and a value model plus a fairness/
  quality business risk (Business) to the PRD.
- The Technology hat did the heavy lifting in Build and Deliver: setting the
  architecture and the API contract, judging whether each artifact was sound, and
  running the quality gates (validate, smoke tests, branch/merge discipline).
- The throughline: the personas executed within their lanes, but the cross-cutting
  decisions (architecture, contracts, scope, what is good enough to merge, which
  risks are acceptable) were mine. That coordination and judgment, not the code
  output, is where the role adds value, operating "above the algorithm" rather than
  competing with it.

Recommendations for future projects:
- Resolve the highest-leverage Open Questions (here, the scoring rubric) before Build.
- Keep the live-key-dependent paths clearly scoped and documented so "not yet run" is
  never mistaken for "passed."
- Let the security assessment feed concrete Deliver defaults (bind address, rate
  limits, spend caps) rather than treating it as a checkbox.
