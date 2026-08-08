# Recruitment Assistant

An automated candidate sourcing and evaluation multi-agent system built on the CrewAI Recruitment Example. Given a set of job requirements, the Recruitment Assistant sources a pool of candidates, scores each one against the job criteria with supporting evidence, and returns a ranked shortlist with clear rationale for a recruiter to review.

**Value proposition:** staged, explainable evaluation that reduces time-to-shortlist and improves scoring consistency, while keeping the final hiring decision with the human. Unlike single-shot AI resume screeners, it separates sourcing, evaluation, and recommendation into connected stages so every ranking is traceable to the scores and evidence produced upstream.

## Problem Statement

Manual candidate sourcing and evaluation is slow, inconsistent, and does not scale. Recruiters spend hours screening resumes per requisition, and evaluation quality varies between reviewers. High-volume roles make the problem worse. Existing tools tend to score candidates in isolation without transparent reasoning, so recruiters cannot easily see why one candidate ranks above another.

This matters because screening time is a direct cost, inconsistent evaluation risks missing strong candidates, and opaque scoring erodes recruiter trust and creates legal and compliance exposure in a regulated hiring domain. A defensible, evidence-based shortlist addresses all three.

## Features

Three P0 capabilities make up the MVP:

- **Candidate search from job requirements.** The recruiter enters job requirements and the system sources a structured pool of matching candidate profiles from the dataset. Ambiguous requirements are surfaced for clarification or handled with explicitly stated assumptions rather than failing silently.
- **Automated evaluation and scoring with per-criterion evidence.** Each sourced candidate is scored against the defined job criteria. Every score carries supporting evidence referencing the candidate profile, and scoring is kept reproducible under the same inputs.
- **Ranked recommendations with rationale.** The system returns a ranked shortlist ordered by evaluation score. Each shortlisted candidate includes an evidence-based rationale and a per-criterion breakdown showing which criteria the candidate fully met, partially met, or missed, so the recruiter can see the "why" behind each ranking. Near-ties use a stable, documented tie-break and are flagged for a closer look. Final hiring decisions remain with the human.

## Architecture Overview

The product is an **Application Crew**: three CrewAI agents that run as a sequential process with context chaining, where each task passes its output to the next via `Task.context`. All agents use `allow_delegation=false` in the MVP, and the coordinator sequences the tasks deterministically.

- **Researcher (Candidate Sourcing Researcher):** the first task. Sources and compiles a pool of candidate profiles that match the job requirements, then passes a structured candidate list to the Evaluator.
- **Evaluator (Candidate Evaluator):** the second task. Consumes the Researcher output and scores each candidate against the fixed job criteria, recording evidence for every score. Runs at low temperature for consistent scoring.
- **Recommender (Shortlist Recommender):** the final task. Consumes the Evaluator output, ranks the candidates, and produces the shortlist with per-candidate rationale and the per-criterion breakdown presented to the recruiter.

They collaborate as a pipeline: Researcher sources, then Evaluator scores, then Recommender ranks and explains.

Note: the **Application Crew** (Researcher, Evaluator, Recommender) is the shipped product. It is distinct from the **Development Crew**, the AAMAD personas (@product-mgr, @system.arch, @backend.eng, and others) that build the product.

## Getting Started

**Prerequisites:**

- Python 3.9+ (developed and tested on 3.12)
- git
- An OpenAI API key (or other LLM provider key), provided via an environment variable and never committed

**Setup:**

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (AAMAD_TARGET_RUNTIME=crewai)
cp .env.example .env
# Edit .env and set OPENAI_API_KEY to your real key
```

**Run the application (local):**

```bash
python main.py
# then open http://127.0.0.1:8000 in your browser
```

**Run with Docker:**

```bash
docker build -t recruitment-assistant .
docker run --env-file .env -p 127.0.0.1:8000:8000 recruitment-assistant
```

The single FastAPI service serves both the web UI (at `/`) and the API. Enter job requirements and criteria, submit, and the Application Crew returns a ranked shortlist with per-candidate rationale and a per-criterion breakdown. Full operational detail is in [deploy.md](project-context/3.deliver/deploy.md); an end-user manual is in [user-guide.md](project-context/3.deliver/user-guide.md).

**API endpoints:**

- `GET /health` - liveness check, returns `{"status":"ok"}`.
- `POST /api/recommend` - body `{ job_requirements, criteria?, top_n? }`; returns `{ shortlist: [ { candidate, rank, score, rationale, criteria_breakdown } ], run_id, status }`. Fails closed with `{ error: { code, message } }` (no partial shortlist).

**Tests:** `pytest` runs an offline smoke suite (`tests/test_smoke.py`) that checks health, static serving, and input validation without making any LLM calls.

Note: without a valid `OPENAI_API_KEY`, the app still boots and `/health` works; `/api/recommend` returns a clear `missing_api_key` error rather than crashing. A live ranked shortlist requires your key.

## Project Structure

This project uses the AAMAD framework layout:

```
recruitment-assistant/
├── .cursor/
│   ├── agents/           # Development Crew persona definitions
│   ├── rules/            # AAMAD core + runtime adapter rules
│   └── templates/        # PRD, SAD, MRD templates
├── config/
│   ├── agents.yaml       # CrewAI Researcher, Evaluator, Recommender agents
│   └── tasks.yaml        # Three sequential tasks (context-chained)
├── src/
│   ├── app.py            # FastAPI app: /api/recommend, /health, static mount
│   ├── crew.py           # Builds and runs the CrewAI Application Crew
│   └── static/           # Minimal web UI (index.html, app.js, styles.css)
├── data/
│   └── candidates.json   # Synthetic candidate dataset (no real PII)
├── tests/
│   └── test_smoke.py     # Offline smoke tests (no LLM calls)
├── project-context/
│   ├── 1.define/         # mrd.md, prd.md, sad.md
│   ├── 2.build/          # backend.md, frontend.md, integration.md, qa.md, security.md
│   └── 3.deliver/        # deploy.md, execution-results.md, user-guide.md
├── main.py               # Local entry point (uvicorn)
├── Dockerfile            # Container image
├── docker-compose.yml    # Single-service compose stack
├── requirements.txt
├── .env.example          # Environment template (copy to .env)
├── LESSONS.md            # Lessons learned across the project
├── AGENTS.md             # Bridge file for IDE agent discoverability
├── CHECKLIST.md          # Define, Build, Deliver workflow checklist
└── README.md
```

Key artifacts:

- `project-context/1.define/` - `mrd.md`, `prd.md` (Agentic-Architect-reviewed), `sad.md`
- `project-context/2.build/` - `backend.md`, `frontend.md`, `integration.md`, `qa.md`, `security.md`
- `project-context/3.deliver/` - `deploy.md`, `execution-results.md`, `user-guide.md`
- `LESSONS.md` - reflection across Define, Build, and Deliver

## Development Status

- **Define phase: complete.** MRD and PRD done; PRD reviewed by the Agentic Architect (Experience and Business hats).
- **Build phase (Module 06): complete.** SAD, CrewAI Application Crew and FastAPI backend, minimal web UI, integration, and a QA smoke pass (`aamad validate --phase build` passes). Offline smoke tests pass; the live ranked-shortlist path requires an `OPENAI_API_KEY` and is documented as scoped future validation in `qa.md`.
- **Deliver phase (Module 07): complete.** Security assessment (SHIP for the synthetic-data MVP), deploy runbook and Docker/local configs, structured logging with CrewAI tracing, an end-to-end local run captured in `execution-results.md`, a user guide, and `LESSONS.md`. `aamad validate --phase deliver` passes. The live LLM shortlist path remains gated on an `OPENAI_API_KEY`.

**Runtime:** `AAMAD_TARGET_RUNTIME=crewai`.

## Lessons Learned

See [LESSONS.md](LESSONS.md) for the full reflection. In short: defining the MRD/PRD first kept the build on-target; single-responsibility personas handing off through canonical artifacts made the multi-agent build coherent and auditable; and the Agentic Architect value was in the cross-cutting decisions (architecture, contracts, scope, risk) and quality gates, not in producing the code itself.
