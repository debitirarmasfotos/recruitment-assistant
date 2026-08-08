# Market Research Document (MRD): Recruitment Assistant

## Context & Instructions

This MRD supports an MVP mini-project: a Recruitment Assistant, an automated candidate sourcing and evaluation multi-agent system based on the CrewAI Recruitment Example. It is scoped as a commercial / market-facing product, so the MRD is intentionally kept rather than skipped.

The selected runtime for the generated application is an implementation choice, not the AAMAD methodology. This document keeps claims qualitative and honest: it does not invent precise market statistics or fabricate source citations. Missing figures are recorded under Open Questions.

## Research Query Structure

**Primary Focus**: Recruitment Assistant, a multi-agent system for automated candidate sourcing, evaluation, and ranked recommendation for recruiters.
**Selected Runtime**: crewai

## Research Dimensions

### 1. Market Analysis & Opportunity Assessment

- **Market Size**: The recruiting and talent-acquisition software market (ATS, sourcing tools, AI screening) is large and established, with sustained investment in automation. Precise sizing is deferred to Open Questions rather than invented here.
- **Growth Trends**: Adoption of AI-assisted screening and sourcing is a visible, ongoing trend as teams face higher applicant volumes and pressure to reduce cost-per-hire. Direction is upward; exact growth rates are deferred.
- **Market Gaps**: Many tools do single-shot resume scoring with limited transparency. A gap exists for a coordinated, explainable pipeline that sources, evaluates, and justifies a shortlist as connected steps.
- **Target Audience**: Primary users are recruiters (in-house and agency). Secondary users are hiring managers who consume the shortlist and rationale. High-volume HR teams are a strong fit because their pain scales with applicant count. Willingness to pay is tied to measurable time savings and shortlist quality; specific pricing sensitivity is deferred.
- **Business Case**: Value comes from reducing hours spent on manual screening, improving consistency of evaluation, and producing a defensible, traceable shortlist. ROI is framed qualitatively as recruiter time reclaimed per requisition.
- **Competitive Landscape**: See Innovation & Differentiation for detail. Alternatives include Applicant Tracking Systems (ATS), LinkedIn Recruiter, manual spreadsheet-driven screening, and single-shot AI resume screeners.

### 2. Technical Feasibility & Requirements Analysis

- **Runtime Capabilities**: CrewAI fits well. The problem is a natural sequential pipeline (source, then evaluate, then recommend) with explicit context chaining between tasks, which matches CrewAI sequential process and Task.context handoffs.
- **Agent Architecture Patterns**: A three-role crew (Researcher, Evaluator, Recommender) using a sequential process with `allow_delegation=false` is a proven, low-complexity pattern for MVP scope.
- **Integration Requirements**: MVP relies on synthetic / sample candidate data and job-requirement input. Live sourcing connectors (job boards, LinkedIn, ATS APIs) are out of scope for the mini-project and deferred.
- **Scalability Considerations**: Bottlenecks are LLM latency and per-candidate token cost. MVP handles modest batch sizes; scaling strategies (batching, caching, ranking heuristics) are deferred.
- **Technical Risks**: LLM scoring variance, prompt sensitivity, and fairness / bias in evaluation. Mitigations: fixed evaluation criteria, low temperature for scoring, evidence-based rationale, and synthetic data only for the MVP.
- **Infrastructure Needs**: Minimal for MVP. A single service running the crew with an LLM API key. Detailed hosting and compute are deferred to the Build and Deliver phases.

### 3. User Experience & Workflow Analysis

- **User Journey Mapping**: Recruiter enters job requirements, the crew sources candidates, evaluates each against criteria, and returns a ranked shortlist with per-candidate rationale that the recruiter reviews.
- **Interface Requirements**: A simple input for job requirements and a readable ranked-results view. Full UI specification is a Build-phase concern.
- **Automation Opportunities**: Sourcing, scoring, and ranking are strong candidates for automation. Final hiring decisions remain human.
- **Human-in-the-Loop**: The recruiter is the decision-maker. The system recommends; it does not auto-reject or contact candidates.
- **Success Metrics**: Time-to-shortlist reduction, share of shortlisted candidates the recruiter advances, and consistency / traceability of scoring. Numeric targets are deferred to the PRD Open Questions.
- **User Adoption Factors**: Enablers are time savings and transparent rationale. Barriers are trust in AI scoring and fairness / bias concerns.

### 4. Production & Operations Requirements

- **Deployment Architecture**: Smallest MVP-appropriate target (single service). Detailed deployment is owned by the Deliver phase.
- **Monitoring & Observability**: Log crew runs, per-task outputs, and scoring rationale for auditability. Specifics are deferred to Build / Deliver.
- **Security Considerations**: Candidate data is PII-sensitive. MVP uses synthetic / sample data only and stores no real candidate records. No secrets in artifacts.
- **Maintenance & Updates**: Criteria and prompts should be adjustable without code changes where feasible. Detailed versioning deferred.
- **Cost Structure**: Primary variable cost is LLM token usage per requisition. Precise cost modeling deferred.
- **Risk Assessment**: Main operational risks are biased or inconsistent scoring and over-reliance on automation. Addressed via evidence-based rationale and human review.

### 5. Innovation & Differentiation Analysis

- **Unique Value Propositions**: A coordinated multi-agent crew that treats sourcing, evaluation, and recommendation as connected stages, producing a ranked shortlist with traceable, evidence-based rationale for each candidate.
- **Differentiation vs Alternatives**:
  - ATS: strong at tracking and workflow, weak at active sourcing and reasoned scoring. The Recruitment Assistant adds evaluation and explainable ranking.
  - LinkedIn Recruiter: strong sourcing reach, but manual screening effort remains high and scoring is not automated or explained per criteria.
  - Manual processes: slow, inconsistent, and hard to scale for high-volume roles.
  - Single-shot AI resume screeners: score in isolation with limited transparency. The multi-agent crew separates sourcing, evaluation, and recommendation, chains context between them, and exposes rationale at each step.
- **Emerging Technologies**: LLM-based reasoning and structured multi-agent orchestration make explainable, staged evaluation practical.
- **Patent Landscape**: Not assessed for this mini-project. Deferred.
- **Future Trends**: Growing expectation of fairness, explainability, and auditability in hiring tools favors a transparent, rationale-first design.
- **Monetization Strategies**: Plausible models include per-seat subscription for recruiters or usage-based pricing per requisition. Specific pricing is deferred.

## Output Format Requirements

### Executive Summary

Manual candidate sourcing and evaluation is slow, inconsistent, and does not scale. Recruiters spend hours screening resumes, and results vary between reviewers. There is a clear opportunity for an assistant that reduces screening time, improves consistency, and scales to high-volume roles, especially where existing tools score candidates in isolation without transparent reasoning.

Technically, the problem maps cleanly onto a sequential multi-agent pipeline. A Researcher sources candidates from job requirements, an Evaluator scores each against the criteria, and a Recommender produces a ranked shortlist with rationale. CrewAI sequential process with context chaining is a strong, low-complexity fit for the MVP, and feasibility is high given the small, well-bounded scope.

The recommended approach is to build a focused MVP with three collaborating agents, synthetic / sample candidate data, fixed evaluation criteria, and evidence-based rationale. Differentiation comes from staged, explainable evaluation rather than single-shot scoring. Quantitative market sizing and numeric success targets are deferred to Open Questions to keep claims honest.

### Detailed Findings by Dimension

Key insights per dimension are captured in sections 1-5 above. Because this is a course mini-project, specific data points, statistics, and source citations are not fabricated; where a number would normally appear, the claim is stated qualitatively and the missing figure is listed under Open Questions.

### Critical Decision Points

- **Go/No-Go Factors**: Availability of representative synthetic candidate data and clearly defined evaluation criteria. Both are achievable for the MVP.
- **Technical Architecture Choices**: CrewAI sequential process, three agents, `allow_delegation=false`, context chaining between tasks.
- **Market Positioning**: Explainable, staged evaluation for recruiters and high-volume HR teams, differentiated from single-shot screeners.
- **Resource Requirements**: Small team and short timeline consistent with a mini-project.

### Risk Assessment Matrix

- **High Risk**: Fairness / bias in automated scoring; mishandling of candidate PII.
- **Medium Risk**: Scoring inconsistency and prompt sensitivity; LLM cost and latency at scale.
- **Low Risk**: MVP UI polish and non-core integrations (deferred).

### Actionable Recommendations

- **Immediate Next Steps**: Define evaluation criteria and prepare synthetic candidate data; finalize the PRD.
- **Short-term Priorities**: Build the three-agent sequential crew with rationale output and human review of the shortlist.
- **Long-term Strategy**: Add live sourcing connectors, ATS integration, and analytics once the MVP proves value.

## Sources

- No external sources were cited. This is an MVP course mini-project and intentionally avoids fabricated citations or invented statistics. Claims are grounded in reasoning about the recruiting workflow and the CrewAI Recruitment Example. Authoritative market data should be gathered before any real go-to-market decision (see Open Questions).

## Assumptions

- The MRD is kept because the project is framed as a commercial / market-facing product, even though it is delivered as a mini-project.
- Market sections are abbreviated and qualitative by design; missing quantitative figures are recorded under Open Questions rather than invented.
- The MVP uses synthetic / sample candidate data only, with no real candidate PII.
- The selected runtime is crewai; Build-phase implementation occurs later (Module 06).

## Open Questions

- What is the current and projected market size for AI-assisted sourcing and screening tools (specific figures and sources)?
- What are realistic industry benchmarks for recruiter screening time per requisition, cost-per-hire, and time-to-fill?
- What percentage time-to-shortlist reduction would constitute clear MVP success?
- What is the target buyer's willingness to pay and preferred pricing model (per-seat vs per-requisition)?
- Which sourcing channels (job boards, LinkedIn, ATS exports) matter most for a future non-MVP version?
- Are there patent or IP considerations for explainable multi-agent evaluation?

## Audit

- 2026-08-08, product-mgr, create-mrd, resolved runtime crewai
