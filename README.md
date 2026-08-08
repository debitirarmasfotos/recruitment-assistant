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

- Python 3.9+
- git
- An LLM API key provided via an environment variable (never committed; see `.env.example` in the Build phase for the required variable names)

**Install and initialization:** the runtime is CrewAI (`AAMAD_TARGET_RUNTIME=crewai`). Build-phase project setup, dependency installation, and run instructions are produced during Module 06 (Build). Until then there are no application run commands to invoke.

**Usage:** to be completed in the Build phase. Run commands and the end-to-end workflow will be documented in `project-context/2.build/` (setup and backend artifacts) once implementation begins.

## Project Structure

This project uses the AAMAD framework layout:

```
recruitment-assistant/
├── .cursor/
│   └── templates/        # PRD, SAD, MRD templates
├── project-context/
│   ├── 1.define/         # Define-phase artifacts (mrd.md, prd.md)
│   ├── 2.build/          # Build-phase artifacts (Module 06)
│   └── 3.deliver/        # Deliver-phase artifacts (Module 07)
├── AGENTS.md             # Bridge file for IDE agent discoverability
├── CHECKLIST.md          # Define, Build, Deliver workflow checklist
└── README.md
```

Key artifacts:

- `project-context/1.define/mrd.md` - Market Research Document
- `project-context/1.define/prd.md` - Product Requirements Document (reviewed by the Agentic Architect)

## Development Status

- **Define phase: complete.** The MRD and PRD are done, and the PRD has been reviewed by the Agentic Architect (Experience and Business hats) and adjusted in place.
- **Build phase (Module 06): next.** Architecture (SAD), setup, the CrewAI backend crew, frontend, integration, and QA.
- **Deliver phase (Module 07): after Build.** Deploy configuration, runbook, and user guide.
