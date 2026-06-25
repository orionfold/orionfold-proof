"""Domain models — the single source of truth for the proof loop.

Per ADR-0001, Pydantic models are shared by the engine, scoring, leaderboard, receipt
exporter, and the FastAPI schema. Every object that crosses the provider boundary or lands
in a receipt is defined here so the whole slice stays consistent and validated.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Privacy = Literal["local", "cloud"]
RubricKind = Literal["exact", "contains", "similarity", "keypoint", "judge", "bench", "none"]
# A bench row's declared behavior contract (governance scoring; see scoring/bench.py).
BenchBehavior = Literal["answer", "route", "refuse"]


class Example(BaseModel):
    """A single frozen input/expected pair the candidates are proven against.

    The trailing ``bench``/advisory fields carry a per-row governance contract (citation /
    refusal / route). They are **all defaulted** so an example that doesn't set them is hashed
    byte-identically to one authored before the bench kind existed — ``config_hash`` projects
    only the non-default bench fields (see ``engine._example_hash_fields``).
    """

    input_text: str
    expected_text: str
    keypoints: list[str] = []  # authored required facts; [] = none
    # --- bench/advisory contract (per-row; all defaulted → existing examples hash unchanged) ---
    expected_behavior: BenchBehavior | None = None  # None → graded as "answer" by the bench scorer
    expected_citations: list[str] = []  # ids that must ALL appear (answer/route rows)
    accepted_source_ids: list[str] = []  # defensible-citation superset; non-empty → ANY one passes
    requires_citation: bool = False
    requires_refusal: bool = False
    requires_route: bool = False


class BenchVerdict(BaseModel):
    """The per-row governance verdict from the bench scorer — five gates plus residue diagnostics.

    ``passed`` is the published verdict (citation ∧ refusal ∧ route ∧ ¬leak ∧ ¬private-state).
    ``strict_passed`` additionally requires no residue (alias citation / bare answer). The receipt
    surfaces every field so a bench failure is explainable. See ``scoring/bench.py`` for the rules.
    """

    citation_ok: bool
    refusal_ok: bool
    route_ok: bool
    thinking_leak: bool
    private_state_risk: bool
    alias_residue: bool
    bare_answer: bool
    cited_source_ids: list[str]
    passed: bool
    strict_passed: bool


class Corpus(BaseModel):
    """The governed source set a bench dataset grades against (ADR; spec §4).

    ``source_ids`` is the manifest of legal citation targets. v0 uses it for provenance and a
    cheap integrity gate (a bench dataset's ``expected_citations``/``accepted_source_ids`` must
    be drawn from a known corpus) — **not** retrieval, which is fenced to a later spec.
    """

    id: str
    name: str
    description: str = ""
    source_ids: list[str] = []


class CorpusSource(BaseModel):
    """One source in a corpus, ENRICHED with the title/class/excerpt that a bench dataset flattens
    into its example ``input_text``. This is DERIVED at read time (parsed from the bound examples),
    not authored — the corpus manifest itself stores only ``source_ids``. ``cited_by`` counts the
    examples whose citation gates name this source, so a browser can show "which sources matter."
    """

    id: str
    title: str = ""
    klass: str = Field(default="", alias="class")  # 'class' is a Python keyword; serialize as "class".
    label: str = ""
    excerpt: str = ""
    cited_by: int = 0

    model_config = {"populate_by_name": True}


class Dataset(BaseModel):
    """A small, frozen set of examples (text-only in v0)."""

    id: str
    name: str
    description: str = ""
    examples: list[Example]
    # A bench dataset binds a governing Corpus by id; non-bench datasets leave this None.
    # Provenance recorded in the receipt — NOT a config_hash input (see engine.config_hash).
    corpus_id: str | None = None
    # An optional governing system prompt the dataset ships with (e.g. a bench's
    # citation/refusal/route contract). When present, the run applies it to every candidate so the
    # dataset is turnkey. Dataset-level field is hash-inert (provenance, like corpus_id); the prompt
    # enters config_hash only via the candidate it is applied to (engine._candidate_hash_fields).
    system_prompt: str | None = None


class Rubric(BaseModel):
    """How an output is scored against the expected text.

    ``threshold`` is the minimum score (0..1) for a row to count as passing.
    """

    kind: RubricKind = "similarity"
    threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    case_sensitive: bool = False
    judge_provider_id: str | None = None  # only used when kind == "judge"
    judge_model: str | None = None  # recorded in provenance; shown in the receipt


class Candidate(BaseModel):
    """One thing being proven — a provider with a label and a privacy boundary."""

    id: str
    label: str
    provider_id: str
    privacy: Privacy = "local"
    model: str | None = None
    # A per-candidate system prompt for prompt-variant runs. None → the global TASK_SYSTEM_PROMPT
    # (unchanged behavior). Part of identity → feeds config_hash only when set.
    system_prompt: str | None = None


class PromptVariant(BaseModel):
    """A named system-prompt variant in a 'one model, N prompts' comparison."""

    name: str
    system_prompt: str


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
    """One cell of the run matrix: a candidate's attempt at one example.

    ``score``/``passed`` are ``None`` for an unscored (quick-compare) run — an honest
    absence, never a placeholder zero.
    """

    candidate_id: str
    example_index: int
    input_text: str
    expected_text: str
    output_text: str
    score: float | None
    passed: bool | None
    latency_ms: int
    estimated_cost_usd: float
    input_tokens: int = 0
    output_tokens: int = 0
    privacy: Privacy
    error: str | None = None
    judge_cost_usd: float = 0.0  # cost of the judge call for this cell (0 for non-judge)
    judge_latency_ms: int = 0  # judge latency for this cell (0 for non-judge)
    # Per-gate governance detail for a bench-scored cell (citation/refusal/route/leak/residue).
    # None for every non-bench cell. A RESULT, not config → never enters config_hash.
    bench_detail: BenchVerdict | None = None


class LeaderboardEntry(BaseModel):
    """Aggregated standing for one candidate across the dataset."""

    candidate_id: str
    label: str
    provider_id: str
    privacy: Privacy
    model: str | None = None
    system_prompt: str | None = None  # set for prompt-variant entries; None for model-compare
    total: int
    pass_count: int
    pass_rate: float
    avg_score: float
    avg_latency_ms: int
    total_estimated_cost_usd: float
    failure_count: int
    error_count: int = 0
    recommended: bool = False
    cost_per_quality: float | None = None  # $ per quality point (cost/avg_score); None if avg_score==0. Presentation only — never affects ranking.
    tokens_per_second: float | None = None  # Σoutput_tokens / Σlatency_s; None when no measured latency. Presentation only — never a ranking key, never in config_hash (the 32GB-Mac-vs-128GB-GB10 generalization metric).


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
    # Quick-compare provenance. Presentation only — EXCLUDED from config_hash so a quick run's
    # hash is identical before and after a pick is recorded.
    mode: Literal["full", "quick"] = "full"
    chosen_winner: str | None = None  # a candidate_id, the literal "tie", or None (no pick yet)


class RunCostSummary(BaseModel):
    """The full cost picture for a run — candidate, judge, and grand total (USD)."""

    candidate_cost_usd: float
    judge_cost_usd: float
    total_cost_usd: float


class ProofReport(BaseModel):
    """The full assembled result: run provenance + leaderboard + every result row.

    This is what the API returns and what the receipt exporter serializes.
    """

    run: ProofRun
    leaderboard: list[LeaderboardEntry]
    results: list[ResultRow]
    cost_summary: RunCostSummary = Field(
        default_factory=lambda: RunCostSummary(
            candidate_cost_usd=0.0, judge_cost_usd=0.0, total_cost_usd=0.0
        )
    )


class TrackRecordEntry(BaseModel):
    """One candidate's standing rolled up across every comparable run in a group.

    "Comparable" means same dataset, same rubric kind (see :class:`TrackRecordGroup`).
    Aggregates read existing :class:`LeaderboardEntry` fields only — no scoring is re-run,
    so this never touches the run engine or ``config_hash``.
    """

    candidate_id: str
    label: str
    provider_id: str
    privacy: Privacy
    model: str | None = None
    runs: int  # how many runs in this group included the candidate
    total_examples: int  # Σ examples scored across those runs
    total_passes: int  # Σ passing examples across those runs
    pass_rate: float  # total_passes / total_examples (0.0 when no examples)
    avg_cost_usd: float  # mean per-run total cost for this candidate
    times_recommended: int  # how many runs in the group crowned this candidate


class TrackRecordGroup(BaseModel):
    """Cross-run standings for one comparable slice: a (dataset, rubric kind) pair.

    The comparability rule (locked in the B4 brainstorm, ADR-0004 §5): only runs over the
    same dataset scored with the same rubric kind roll up together — a similarity pass-rate
    and a judge pass-rate measure different things and must not be averaged.
    """

    dataset_id: str
    dataset_name: str
    rubric_kind: RubricKind
    runs: int  # distinct runs in this group
    entries: list[TrackRecordEntry]  # candidates, best aggregate pass-rate first
