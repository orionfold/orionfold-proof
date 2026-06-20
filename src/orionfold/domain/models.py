"""Domain models — the single source of truth for the proof loop.

Per ADR-0001, Pydantic models are shared by the engine, scoring, leaderboard, receipt
exporter, and the FastAPI schema. Every object that crosses the provider boundary or lands
in a receipt is defined here so the whole slice stays consistent and validated.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Privacy = Literal["local", "cloud"]
RubricKind = Literal["exact", "contains", "similarity"]


class Example(BaseModel):
    """A single frozen input/expected pair the candidates are proven against."""

    input_text: str
    expected_text: str


class Dataset(BaseModel):
    """A small, frozen set of examples (text-only in v0)."""

    id: str
    name: str
    description: str = ""
    examples: list[Example]


class Rubric(BaseModel):
    """How an output is scored against the expected text.

    ``threshold`` is the minimum score (0..1) for a row to count as passing.
    """

    kind: RubricKind = "similarity"
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    case_sensitive: bool = False


class Candidate(BaseModel):
    """One thing being proven — a provider with a label and a privacy boundary."""

    id: str
    label: str
    provider_id: str
    privacy: Privacy = "local"


class ProviderResult(BaseModel):
    """Uniform, error-safe result returned by every provider (ADR-0001 §6).

    ``error`` is populated *instead of* raising across the provider boundary, so one bad
    candidate never aborts a run. ``raw_metadata`` is sanitized — never secrets or keys.
    """

    output_text: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    privacy: Privacy = "local"
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ResultRow(BaseModel):
    """One cell of the run matrix: a candidate's attempt at one example, scored."""

    candidate_id: str
    example_index: int
    input_text: str
    expected_text: str
    output_text: str
    score: float
    passed: bool
    latency_ms: int
    estimated_cost_usd: float
    privacy: Privacy
    error: str | None = None


class LeaderboardEntry(BaseModel):
    """Aggregated standing for one candidate across the dataset."""

    candidate_id: str
    label: str
    provider_id: str
    privacy: Privacy
    total: int
    pass_count: int
    pass_rate: float
    avg_score: float
    avg_latency_ms: int
    total_estimated_cost_usd: float
    failure_count: int
    recommended: bool = False


class ProofBrief(BaseModel):
    """Lightweight framing of the decision this proof informs (not a wizard in v0)."""

    task_name: str
    decision_question: str
    success_criteria: str = ""


class ProofRun(BaseModel):
    """A single matrix run: the brief, dataset, rubric, candidates, and provenance."""

    id: str
    brief: ProofBrief
    dataset_id: str
    dataset_name: str
    rubric: Rubric
    candidates: list[Candidate]
    config_hash: str
    created_at: str
    status: Literal["complete"] = "complete"


class ProofReport(BaseModel):
    """The full assembled result: run provenance + leaderboard + every result row.

    This is what the API returns and what the receipt exporter serializes.
    """

    run: ProofRun
    leaderboard: list[LeaderboardEntry]
    results: list[ResultRow]
