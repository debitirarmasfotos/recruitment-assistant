"""CrewAI crew entrypoint for the Recruitment Assistant MVP.

Builds a three-agent sequential crew (Researcher -> Evaluator -> Recommender)
from externalized YAML config (config/agents.yaml, config/tasks.yaml) per the
CrewAI adapter rules, loads the synthetic candidate pool from
data/candidates.json, and exposes run_recommendation(...) for the API layer.

Design invariants (from SAD section 2 and PRD section 5):
- allow_delegation=false for every agent.
- Process.sequential with explicit Task.context chaining.
- Low temperature for scoring determinism.
- Fail closed: on any failure raise/return a clear error. Never fabricate a
  partial shortlist.
- Secrets (OPENAI_API_KEY / OPENAI_MODEL) come from the environment only.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Optional

import yaml

# Project layout anchors (absolute, resolved from this file).
_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_DIR.parent
_CONFIG_DIR = _PROJECT_ROOT / "config"
_DATA_FILE = _PROJECT_ROOT / "data" / "candidates.json"

# Placeholder values that mean "no real key configured".
_PLACEHOLDER_KEYS = {
    "",
    "your_openai_api_key_here",
    "changeme",
    "sk-xxx",
}

# Default overall score threshold used only to bound near-tie flagging notes.
_NEAR_TIE_MARGIN = 3.0


class RecommendationError(Exception):
    """Raised when a recommendation run cannot be completed.

    Carries a machine-readable ``code`` alongside a human-readable message so
    the API layer can map it into the error envelope.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _api_key_missing() -> bool:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    return key in _PLACEHOLDER_KEYS


def _resolve_model() -> str:
    return (os.getenv("OPENAI_MODEL") or "gpt-4o").strip()


def load_candidates() -> list[dict[str, Any]]:
    """Load the synthetic candidate pool from data/candidates.json."""
    if not _DATA_FILE.exists():
        raise RecommendationError(
            "dataset_missing",
            f"Candidate dataset not found at {_DATA_FILE}.",
        )
    try:
        raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RecommendationError(
            "dataset_invalid",
            f"Candidate dataset is not valid JSON: {exc}",
        ) from exc

    candidates = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(candidates, list) or not candidates:
        raise RecommendationError(
            "dataset_empty",
            "Candidate dataset contains no candidates.",
        )
    return candidates


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RecommendationError(
            "config_missing",
            f"Required config file not found: {path}.",
        )
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise RecommendationError(
            "config_invalid",
            f"Config file {path} is not valid YAML: {exc}",
        ) from exc


def _extract_json(text: str) -> Any:
    """Parse a JSON value from raw LLM text.

    Tolerates accidental code fences even though the tasks request raw JSON,
    then falls back to slicing the outermost object/array. Raises on failure so
    the caller fails closed rather than returning a partial result.
    """
    if text is None:
        raise RecommendationError("output_unparseable", "Crew produced no output.")

    cleaned = text.strip()
    # Strip a leading/trailing ```json ... ``` fence if the model added one.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost {...} or [...] span.
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise RecommendationError(
        "output_unparseable",
        "Could not parse the recommender output as JSON.",
    )


def _normalize_shortlist(parsed: Any, top_n: int) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Coerce the recommender output into the API shortlist contract."""
    if isinstance(parsed, dict):
        shortlist = parsed.get("shortlist", [])
        notes = parsed.get("notes")
    elif isinstance(parsed, list):
        shortlist = parsed
        notes = None
    else:
        raise RecommendationError(
            "output_unparseable",
            "Recommender output was not an object or array.",
        )

    if not isinstance(shortlist, list):
        raise RecommendationError(
            "output_unparseable",
            "Recommender 'shortlist' was not a list.",
        )

    normalized: list[dict[str, Any]] = []
    for idx, entry in enumerate(shortlist[:top_n], start=1):
        if not isinstance(entry, dict):
            continue
        normalized.append(
            {
                "candidate": entry.get("candidate", {}),
                "rank": entry.get("rank", idx),
                "score": entry.get("score"),
                "rationale": entry.get("rationale", ""),
                "criteria_breakdown": entry.get("criteria_breakdown", []),
            }
        )

    if not normalized and not notes:
        notes = "No strong matches were found for the provided job requirements."
    return normalized, notes


def build_crew(inputs: dict[str, Any]):
    """Construct the CrewAI Crew from YAML config.

    Imported lazily so the API layer (and /health) can boot even if crewai is
    not installed in the current environment.
    """
    try:
        from crewai import Agent, Crew, Process, Task
        from crewai import LLM
    except ImportError as exc:
        raise RecommendationError(
            "runtime_unavailable",
            "The crewai package is not installed in this environment. "
            "Install requirements.txt to run recommendations.",
        ) from exc

    agents_cfg = _load_yaml(_CONFIG_DIR / "agents.yaml")
    tasks_cfg = _load_yaml(_CONFIG_DIR / "tasks.yaml")

    model = _resolve_model()
    # Low temperature for scoring determinism (SAD section 2).
    scoring_llm = LLM(model=model, temperature=0.1)
    default_llm = LLM(model=model, temperature=0.2)

    llm_by_agent = {
        "researcher": default_llm,
        "evaluator": scoring_llm,
        "recommender": scoring_llm,
    }

    agents: dict[str, Any] = {}
    for name, cfg in agents_cfg.items():
        agents[name] = Agent(
            role=cfg["role"],
            goal=cfg["goal"],
            backstory=cfg["backstory"],
            allow_delegation=bool(cfg.get("allow_delegation", False)),
            verbose=bool(cfg.get("verbose", False)),
            max_iter=int(cfg.get("max_iter", 12)),
            llm=llm_by_agent.get(name, default_llm),
        )

    # Build tasks in declared order, wiring context chaining by task name.
    tasks: dict[str, Any] = {}
    ordered_task_names = list(tasks_cfg.keys())
    for name in ordered_task_names:
        cfg = tasks_cfg[name]
        agent_name = cfg["agent"]
        if agent_name not in agents:
            raise RecommendationError(
                "config_invalid",
                f"Task '{name}' references unknown agent '{agent_name}'.",
            )
        context_tasks = [tasks[dep] for dep in cfg.get("context", []) if dep in tasks]
        description = cfg["description"].format(**inputs)
        expected_output = cfg["expected_output"]
        tasks[name] = Task(
            description=description,
            expected_output=expected_output,
            agent=agents[agent_name],
            context=context_tasks,
            max_retries=2,
        )

    crew = Crew(
        agents=list(agents.values()),
        tasks=[tasks[name] for name in ordered_task_names],
        process=Process.sequential,
        memory=False,
        max_rpm=30,
        verbose=True,
    )
    return crew


def run_recommendation(
    job_requirements: Any,
    criteria: Optional[list] = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Run the recommendation crew and return the API-shaped result.

    Returns a dict:
      {
        "shortlist": [ {candidate, rank, score, rationale, criteria_breakdown} ],
        "run_id": str,
        "status": "ok",
        "notes": str (optional)
      }

    Fails closed: raises RecommendationError on any problem rather than returning
    a partial or fabricated shortlist.
    """
    run_id = f"run-{uuid.uuid4().hex[:12]}"

    # Validate inputs up front.
    if job_requirements is None or (
        isinstance(job_requirements, str) and not job_requirements.strip()
    ):
        raise RecommendationError(
            "invalid_input",
            "job_requirements is required and must not be empty.",
        )
    if not isinstance(top_n, int) or top_n < 1:
        raise RecommendationError(
            "invalid_input",
            "top_n must be a positive integer.",
        )
    if criteria is not None and not isinstance(criteria, list):
        raise RecommendationError(
            "invalid_input",
            "criteria must be a list when provided.",
        )

    # Fail fast and clearly if no real LLM key is configured, so the app can
    # still boot and serve /health without a key.
    if _api_key_missing():
        raise RecommendationError(
            "missing_api_key",
            "OPENAI_API_KEY is not set (or is a placeholder). A valid OpenAI "
            "API key is required to run a recommendation. Set it in your .env.",
        )

    candidates = load_candidates()

    inputs = {
        "job_requirements": json.dumps(job_requirements)
        if not isinstance(job_requirements, str)
        else job_requirements,
        "criteria": json.dumps(criteria or []),
        "top_n": top_n,
        "candidates": json.dumps(candidates),
    }

    crew = build_crew(inputs)

    try:
        result = crew.kickoff(inputs=inputs)
    except RecommendationError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any runtime failure as a clear error
        raise RecommendationError(
            "runtime_error",
            f"The recommendation run failed: {exc}",
        ) from exc

    raw_output = getattr(result, "raw", None) or str(result)
    parsed = _extract_json(raw_output)
    shortlist, notes = _normalize_shortlist(parsed, top_n)

    response: dict[str, Any] = {
        "shortlist": shortlist,
        "run_id": run_id,
        "status": "ok",
    }
    if notes:
        response["notes"] = notes
    return response
