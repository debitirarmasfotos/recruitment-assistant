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

**Run the application:**

```bash
uvicorn src.app:app --reload
# then open http://localhost:8000 in your browser
```

The single FastAPI service serves both the web UI (at `/`) and the API. Enter job requirements and criteria, submit, and the Application Crew returns a ranked shortlist with per-candidate rationale and a per-criterion breakdown.

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
│   ├── 2.build/          # backend.md, frontend.md, integration.md, qa.md
│   └── 3.deliver/        # Deliver-phase artifacts (Module 07)
├── requirements.txt
├── .env.example          # Environment template (copy to .env)
├── AGENTS.md             # Bridge file for IDE agent discoverability
├── CHECKLIST.md          # Define, Build, Deliver workflow checklist
└── README.md
```

Key artifacts:

- `project-context/1.define/` - `mrd.md`, `prd.md` (Agentic-Architect-reviewed), `sad.md`
- `project-context/2.build/` - `backend.md`, `frontend.md`, `integration.md`, `qa.md`

## Development Status

- **Define phase: complete.** MRD and PRD done; PRD reviewed by the Agentic Architect (Experience and Business hats).
- **Build phase (Module 06): complete.** SAD, CrewAI Application Crew and FastAPI backend, minimal web UI, integration, and a QA smoke pass (`aamad validate --phase build` passes). Offline smoke tests pass; the live ranked-shortlist path requires an `OPENAI_API_KEY` and is documented as scoped future validation in `qa.md`.
- **Deliver phase (Module 07): next.** Deploy configuration, runbook, and user guide.

**Runtime:** `AAMAD_TARGET_RUNTIME=crewai`.
