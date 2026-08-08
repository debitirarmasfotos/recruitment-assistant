# Product Requirements Document (PRD): Recruitment Assistant

## Context & Instructions

This PRD defines the MVP for the Recruitment Assistant, an automated candidate sourcing and evaluation multi-agent system based on the CrewAI Recruitment Example. It is derived from `project-context/1.define/mrd.md`.

The selected runtime (crewai) constrains Phase 2 implementation conventions; it does not define the product itself. This document keeps claims honest, avoids invented statistics, and defers unset numeric targets to Open Questions.

## Input Requirements

**Deep Research Report / MRD**: `project-context/1.define/mrd.md`
**System Description**: N/A (not produced for this mini-project; requirements captured directly in this PRD and the MRD)
**System Concept**: A three-agent CrewAI crew that sources candidates from job requirements, evaluates each against criteria, and produces a ranked shortlist with rationale for a recruiter.
**Selected Runtime**: crewai

## PRD Structure

### 1. Executive Summary

**Problem Statement**:

- Manual candidate sourcing and evaluation is slow, inconsistent, and does not scale. Recruiters spend hours screening resumes per requisition.
- Impact is described qualitatively: high manual effort, variable evaluation quality between reviewers, and difficulty handling high-volume roles. Precise time and cost figures are deferred to Open Questions.
- Target user population: recruiters (in-house and agency), hiring managers, and high-volume HR teams.

**Solution Overview**:

- A coordinated multi-agent crew that sources, evaluates, and recommends as connected stages: Researcher sources candidates, Evaluator scores them against criteria, Recommender ranks and explains the top matches.
- Key differentiator: staged, explainable evaluation with traceable per-candidate rationale, versus single-shot AI resume screeners and manual review.
- Expected outcome: reduced time-to-shortlist, more consistent scoring, and a defensible shortlist the recruiter can trust. Numeric targets are defined in Success Metrics with thresholds deferred to Open Questions.

**Strategic Rationale**:

- Multi-agent architecture is optimal because the work is a natural sequential pipeline with distinct responsibilities and context handoffs between stages, which improves clarity and explainability over a single monolithic prompt.
- Business value: recruiter time reclaimed per requisition and improved shortlist quality and consistency.
- Qualitative ROI / value model (stated in plain terms, no invented numbers): business value roughly equals recruiter hours reclaimed per requisition, times requisition volume, times loaded recruiter cost, plus a quality gain proxied by shortlist advance rate. This gives a defensible ROI framing while the specific numeric thresholds (hours reclaimed, volume, cost, and target advance rate) remain deferred to Open Questions.
- Positioning: explainable, staged evaluation for recruiters and high-volume HR teams. This is a commercial-style scenario delivered as an MVP mini-project.

### 2. Market Context & User Analysis

**Target Market / Users**:

- Primary persona: Recruiter (in-house or agency) who defines job requirements and reviews the shortlist.
- Secondary persona: Hiring Manager who consumes the shortlist and rationale to make interview decisions.
- Additional segment: high-volume HR teams whose pain scales with applicant count.
- Market segment size and geographic focus: N/A for the MVP; deferred to MRD Open Questions.

**User Needs Analysis**:

- Critical pain points: hours spent screening resumes, inconsistent evaluation, and inability to scale.
- User journey: recruiter enters job requirements, the crew sources and evaluates candidates, and returns a ranked shortlist with rationale for review.
- Adoption barriers: trust in AI scoring and fairness / bias concerns. Enablers: measurable time savings and transparent, evidence-based rationale.

**Competitive Landscape**:

- ATS: strong tracking, weak active sourcing and reasoned scoring.
- LinkedIn Recruiter: strong sourcing reach, manual screening effort remains high.
- Manual processes: slow, inconsistent, hard to scale.
- Single-shot AI resume screeners: isolated scoring with limited transparency.
- Differentiation: staged source, evaluate, recommend pipeline with context chaining and per-step rationale. Pricing benchmarks deferred to MRD Open Questions.

### 3. Technical Requirements & Architecture

**Runtime & Agent Specifications** (aligned with crewai):

- Three agents in a sequential CrewAI process: Researcher, Evaluator, Recommender.
- Collaboration pattern: sequential context chaining. Each task passes its output to the next via `Task.context`.
- Delegation boundaries: `allow_delegation=false` for all agents in the MVP. No agent reassigns work; the coordinator sequences tasks deterministically.
- Runtime controls: sequential process mode, low temperature for scoring determinism, `max_iter` kept small (baseline <= 12) per adapter rules, secrets loaded from environment variables.

**Core Agent Definitions (Application Crew)**:

- agent: researcher
  - role: "Candidate Sourcing Researcher"
  - goal: "Source and compile a pool of candidate profiles that match the provided job requirements."
  - tools: candidate data source over synthetic / sample dataset (MVP); optional search tool. No live job-board or ATS connectors in the MVP.
  - runtime notes: first task in the sequential process; `allow_delegation=false`; output is a structured candidate list passed to the Evaluator via context.

- agent: evaluator
  - role: "Candidate Evaluator"
  - goal: "Score each sourced candidate against the defined job criteria and record evidence for every score."
  - tools: evaluation / scoring logic over the fixed criteria; no external write tools.
  - runtime notes: second task; consumes the Researcher output via `Task.context`; `allow_delegation=false`; low temperature for consistent scoring; produces per-candidate scores plus evidence.

- agent: recommender
  - role: "Shortlist Recommender"
  - goal: "Rank the evaluated candidates and produce a shortlist with clear, evidence-based rationale for each recommendation."
  - tools: ranking / formatting logic; no external tools.
  - runtime notes: final task; consumes the Evaluator output via `Task.context`; `allow_delegation=false`; output is the ranked shortlist with rationale presented to the recruiter.

- Collaboration: Researcher sources candidates, then Evaluator scores them against criteria, then Recommender ranks and explains the top matches. Sequential process with explicit context chaining between the three tasks.

**Integration Requirements**:

- Required services: an LLM API (key via environment variable). No external recruiting APIs in the MVP.
- Data / storage: synthetic / sample candidate dataset and job-requirement input. No persistent store of real candidate data.
- Authentication and security: no real candidate PII; secrets never committed; `.env.example` documents required variable names.
- Performance and scalability targets: MVP handles modest candidate batches; scaling deferred.

**Infrastructure Specifications**:

- Hosting: smallest MVP-appropriate target (single service running the crew). Detailed hosting owned by Deliver.
- Compute / memory: minimal; driven by LLM API usage.
- Network / security: least-privilege API key usage; no inbound integrations in the MVP.
- Monitoring / logging: log crew runs, per-task outputs, and rationale for auditability (Build-phase detail).

### 4. Functional Requirements

**Core Features (Priority P0)**:

- Feature 1: Candidate search from job requirements
  - User story: As a recruiter, I want to enter job requirements so that the system sources a pool of matching candidates.
  - Acceptance criteria:
    - Given valid job requirements, when I submit them, then the Researcher returns a structured list of candidate profiles drawn from the synthetic dataset.
    - Given missing or ambiguous requirements, when I submit them, then the system requests clarification or records the ambiguity and proceeds with stated assumptions rather than failing silently.
    - The candidate list is passed to the Evaluator via context chaining.

- Feature 2: Automated evaluation / scoring against criteria
  - User story: As a recruiter, I want each sourced candidate scored against the job criteria so that evaluation is consistent and evidence-based.
  - Acceptance criteria:
    - Given the sourced candidate list and defined criteria, when evaluation runs, then each candidate receives a score against those criteria.
    - Each score includes supporting evidence / rationale referencing the candidate profile.
    - Scoring is deterministic enough to be reproducible under the same inputs (low temperature).

- Feature 3: Ranked recommendations with rationale
  - User story: As a recruiter, I want a ranked shortlist with rationale so that I can quickly decide which candidates to advance.
  - Acceptance criteria:
    - Given scored candidates, when recommendation runs, then the Recommender returns a ranked shortlist ordered by evaluation score.
    - Each shortlisted candidate includes a clear, evidence-based rationale for the ranking.
    - Each shortlisted candidate includes a per-criterion breakdown showing which job criteria the candidate fully met, partially met, or missed, not only an overall score and prose rationale, so the recruiter can see the "why" behind each ranking.
    - Output is presented in a readable ranked format for recruiter review; final hiring decisions remain with the human.

**Enhanced Features (Priority P1)**:

- Deferred for the MVP. Candidate-facing communication and richer filtering are not included.

**Future Features (Priority P2)**:

- Full ATS integration.
- Candidate communication automation.
- Advanced analytics and reporting.
- Live sourcing connectors (job boards, LinkedIn, ATS exports).

### 5. Non-Functional Requirements

**Performance Requirements**:

- Response time: complete a run for a modest candidate batch within a reasonable interactive window; exact target deferred to Open Questions.
- Throughput / concurrency: single-run MVP; concurrency deferred.
- Availability: no formal uptime target for the MVP.

**Security & Compliance**:

- Data protection: the MVP uses synthetic / sample candidate data only. No real candidate PII is ingested or stored.
- Fairness / bias awareness: evaluation must use fixed, job-relevant criteria and produce evidence-based rationale. The system recommends; it does not auto-reject or contact candidates. Bias risk is called out explicitly and human review is required.
- Access control: secrets provided via environment variables and never committed; least-privilege API key usage.
- Regulatory compliance: hiring-domain regulations (for example fairness in automated decisioning) are noted as a real concern for any production version and deferred beyond the MVP.

**Scalability & Reliability**:

- Scaling triggers: deferred; MVP targets small batches.
- Fault tolerance: on agent or LLM failure, halt the run and surface a clear error to the recruiter rather than returning a partial or misleading shortlist.

### 6. User Experience Design

**Interface Requirements**:

- Recruiter inputs job requirements through a simple input (form or prompt). Detailed UI is a Build-phase concern.
- Results are presented as a ranked list with per-candidate rationale.
- Usability: output must be scannable so a recruiter can quickly assess the top matches.

**Agent Interaction Design**:

- Input: the recruiter provides job requirements (role, key skills, criteria).
- Output presentation: a ranked shortlist where each candidate shows their rank, score, an evidence-based rationale, and a per-criterion breakdown indicating which job criteria the candidate fully met, partially met, or missed, so the recruiter can see the "why" behind each ranking rather than only an overall score.
- Ambiguous requirements: the system asks for clarification where feasible, or proceeds with explicitly stated assumptions rather than guessing silently.
- Errors / edge cases: no matching candidates returns an explicit "no strong matches" result with reasoning; agent or LLM errors halt the run with a clear message; malformed input is rejected with guidance.
- Near-ties: when candidates have effectively equal scores, the shortlist applies a stable, documented tie-break (for example, higher count of fully-met criteria first, then a stable ordering) rather than arbitrary ordering, and flags the near-tie so the recruiter knows to look closer.
- Tone / brand: agent output is professional, unbiased, and evidence-based. Rationale references candidate evidence and job criteria, avoids unsupported claims, and does not use language that introduces bias.
- Transparency: every recommendation is traceable to the scores and evidence produced upstream.

### 7. Success Metrics & KPIs

**Business / Operational Metrics**:

- Time-to-shortlist reduction: measure recruiter time from submitting job requirements to having a reviewable shortlist, compared against a manual baseline. Target threshold deferred to Open Questions.
- Shortlist advance rate: percentage of shortlisted candidates the recruiter advances to the next stage, measured from recruiter actions on the shortlist. Target threshold deferred to Open Questions.
- Scoring consistency / traceability: proportion of scores that carry supporting evidence and reproduce under the same inputs. Target: every score should carry rationale; the exact consistency threshold is deferred.

**Technical Metrics**:

- Run reliability: percentage of runs that complete without error on valid input.
- Reproducibility: score variance across repeated runs on identical inputs kept low (low-temperature scoring).
- Cost efficiency: LLM token usage per requisition tracked; target deferred.

**User Experience Metrics**:

- Recruiter satisfaction with shortlist relevance and rationale clarity (qualitative for the MVP).
- Task completion: recruiter can go from requirements to a reviewed shortlist in a single session.
- Time-to-value: measured by the time-to-shortlist metric above.

### 8. Implementation Strategy

**Development Phases**:

- Phase 1 (Define): MRD (kept), this PRD, then SAD by @system.arch.
- Phase 2 (Build, Module 06): setup, backend crew, frontend, integration, QA.
- Phase 3 (Deliver, Module 07): deploy configuration, runbook, and user guide.

**Development Crew Mapping** (builds the system; distinct from the Application Crew, which is the shipped product):

- @product-mgr: Define phase, now (this PRD and the MRD).
- @system.arch: SAD and SFS.
- @backend.eng: implements the CrewAI Researcher, Evaluator, Recommender crew (Build, Module 06).
- @frontend.eng: recruiter input and ranked-results UI (Build, Module 06).
- @integration.eng: connects frontend and backend (Build, Module 06).
- @qa.eng: validates MVP functionality against acceptance criteria (Build, Module 06).
- @devops.eng: deploy configuration, runbook, and user guide (Deliver, Module 07).

Note: the Development Crew (the AAMAD personas above) builds the product. The Application Crew (Researcher, Evaluator, Recommender) is the shipped multi-agent product itself.

**Resource Requirements and Risk Mitigation**:

- Resources: small team, short timeline, LLM API access. Consistent with a mini-project.
- Risk mitigation: synthetic data only (PII risk); fixed criteria plus low temperature (consistency risk); evidence-based rationale and mandatory human review (bias and over-automation risk).
- Business risk (fairness / quality): perceived bias or low shortlist quality erodes recruiter trust and creates legal and compliance exposure, since automated hiring is a regulated, high-scrutiny domain. This directly threatens adoption and the ROI framing above. Mitigations: mandatory human-in-the-loop final decision, fixed job-relevant criteria, evidence-based rationale, and synthetic data in the MVP. Shortlist advance rate is named as the leading indicator of recruiter trust and serves as a go/no-go signal for scaling beyond the MVP.

### 9. Launch & Go-to-Market Strategy

N/A for the MVP mini-project. Go-to-market and pricing are deferred (see MRD Open Questions). Recorded as N/A under Assumptions.

## Quality Assurance Checklist

- [x] Requirements traceable to MRD or recorded Assumptions
- [x] Technical specifications feasible with the crewai runtime adapter
- [x] Success metrics aligned with stated objectives (thresholds deferred to Open Questions)
- [x] MVP vs Future Work boundaries explicit
- [x] Market sections retained because the MRD was kept (commercial-style scenario)

## Sources

- `project-context/1.define/mrd.md` (Recruitment Assistant MRD)
- CrewAI Recruitment Example (conceptual basis for the three-agent pipeline)
- No external statistics or citations were invented; unknowns are recorded under Open Questions.

## Assumptions

- This is a commercial-style scenario, so the MRD was kept (not skipped).
- The MVP uses synthetic / sample candidate data only; no real candidate PII is ingested or stored.
- No separate system-description document was produced; requirements are captured in this PRD and the MRD.
- Launch / go-to-market is N/A for the mini-project.
- The selected runtime is crewai; Build-phase implementation occurs in Module 06.
- This PRD was reviewed by the Agentic Architect (Experience and Business hats) and adjusted in place: a per-criterion breakdown requirement for the shortlist, near-tie tie-break handling, a qualitative ROI / value model, and an explicit fairness / quality business risk with shortlist advance rate as the leading trust indicator.

## Open Questions

- What is the target time-to-shortlist reduction versus the manual baseline (numeric threshold)?
- What shortlist advance rate defines MVP success?
- What is the acceptable maximum run time for a modest candidate batch?
- What scoring consistency threshold (variance across identical runs) is acceptable?
- What is the target LLM cost per requisition?
- Which specific job-relevant criteria and scoring rubric should the Evaluator use, and who owns approving them?
- What is the expected candidate batch size for a typical MVP run?
- What structure and size should the synthetic candidate dataset have to be representative?

## Audit

- 2026-08-08, product-mgr, create-prd, resolved runtime crewai
- 2026-08-08, product-mgr, architect-review-adjustments, resolved runtime crewai. Folded in four approved Agentic Architect adjustments (Experience and Business hats): (1) added a per-criterion met/partially-met/missed breakdown to Feature 3 acceptance criteria and mirrored it in the section 6 output-presentation bullet; (2) added near-tie handling with a stable, documented tie-break and near-tie flagging to section 6 errors / edge cases; (3) added a qualitative ROI / value model to the section 1 Strategic Rationale (recruiter hours reclaimed times requisition volume times loaded cost, plus a quality gain proxied by shortlist advance rate), thresholds still deferred to Open Questions; (4) added an explicit fairness / quality business risk to section 8, naming shortlist advance rate as the leading recruiter-trust indicator and go/no-go signal, with human-in-the-loop, fixed criteria, evidence-based rationale, and synthetic-data mitigations.
