# Prompt-variant candidates (#6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a comparison axis that holds the model fixed and varies the system prompt — "one model, N prompts" — so an operator can prove which wording of their instructions produces the most trustworthy output on their own dataset.

**Architecture:** A system prompt becomes a field on `Candidate`. A prompt variant is therefore *just a candidate*, so the existing 2-D candidate-major matrix, streaming progress, leaderboard, scoring, and failure-case browser all work unchanged. A `Compare by: Models | Prompts` toggle in the cockpit selects the axis; in Prompts mode the run sends one model id plus a list of named prompts, which the server fans out into one candidate per prompt.

**Tech Stack:** Python 3.12 / FastAPI / Pydantic / pytest (backend); Vite / React / TypeScript / Tailwind v4 / Zod / Vitest / Playwright (frontend).

## Global Constraints

- **Keyless invariant:** the unit + e2e suites run with NO API keys. Mocks ignore the system prompt (stay deterministic); a keyless prompt-compare run on a mock proves plumbing, not score differentiation.
- **No new provider machinery:** reuse the existing `safe_generate` → `provider.generate(example, candidate)` path; only the system-prompt source changes.
- **Secrets:** prompt text is author-written instructions, never a key. The judge/API-key redaction path is untouched; `Rubric`/receipts carry no key field.
- **config_hash:** include `system_prompt` in the per-candidate dict **only when non-None**, so existing model-compare runs hash byte-for-byte identically (zero sample churn).
- **RECEIPT_VERSION:** bump `5 → 6` (any receipt-schema change bumps it). Old persisted reports must still deserialize (new fields are additive/optional).
- **Leaderboard rules unchanged:** never recommend a 0-pass/all-errored candidate; "No clear winner" neutral state; errored rows say "errored, no output".
- **Identity:** a variant candidate id is `{model_candidate_id}#{slug}` (`#` distinct from the `:` model split); slugs deduped (`-2`, `-3`).
- **Tailwind v4:** CSS vars use the PARENTHESIS shorthand `bg-(--color-x)`, never `bg-[--color-x]`.
- **Test-contract strings stay intact:** "Orionfold Proof", "Connected", button `/Run proof/`, regions Leaderboard / Failure cases / Proof Receipt export, "Export Markdown|HTML|JSON", "100% (5/5)", "Failure cases (5)", "simulated provider failure".
- **Verify gate per the HANDOFF:** `uv run pytest`, `uv run ruff check src tests`, `pnpm --dir web test`, `pnpm --dir web build`, and the Playwright e2e (rebuild the embed via `bash scripts/build.sh` FIRST). uvicorn does NOT hot-reload backend code — restart `orionfold up` after backend changes.

---

### Task 1: `Candidate.system_prompt`, `PromptVariant` model, and provider threading

**Files:**
- Modify: `src/orionfold/domain/models.py:48-61` (Candidate) + add `PromptVariant`
- Modify: `src/orionfold/providers/http.py:81-84` (add `system_prompt_for`)
- Modify: `src/orionfold/providers/anthropic.py:44`, `openai_compatible.py:53`, `gemini.py:39`, `ollama.py:38`
- Test: `tests/unit/test_providers_http.py` (append)

**Interfaces:**
- Produces: `Candidate.system_prompt: str | None = None`; `PromptVariant(name: str, system_prompt: str)`; `system_prompt_for(candidate: Candidate) -> str`.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_providers_http.py`:

```python
def test_system_prompt_for_falls_back_to_task_default():
    from orionfold.providers.http import TASK_SYSTEM_PROMPT, system_prompt_for

    assert system_prompt_for(_candidate("ollama", "llama3.2")) == TASK_SYSTEM_PROMPT
    custom = Candidate(id="x", label="x", provider_id="ollama", model="llama3.2",
                       system_prompt="Be terse.")
    assert system_prompt_for(custom) == "Be terse."


def test_providers_send_the_candidates_system_prompt(monkeypatch):
    # Each provider must put the candidate's system_prompt on the wire when set, in the
    # provider-specific slot. Capture the outgoing payload for all four wire shapes.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.clear()
        captured.update(json or {})
        body = {
            "content": [{"type": "text", "text": "ok"}], "usage": {"input_tokens": 1, "output_tokens": 1},
            "choices": [{"message": {"content": "ok"}}], "usage_openai": {},
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}], "usageMetadata": {},
            "message": {"content": "ok"}, "prompt_eval_count": 1, "eval_count": 1,
        }
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(http_mod.httpx, "post", fake_post)
    cand = lambda pid, m: Candidate(id="v", label="v", provider_id=pid, model=m,
                                    system_prompt="VARIANT-SYS-PROMPT")

    AnthropicProvider().generate(_example(), cand("anthropic", "claude-haiku-4-5"))
    assert captured["system"] == "VARIANT-SYS-PROMPT"

    OpenAICompatibleProvider(id="openai", label="OpenAI", base_url="https://api.openai.com/v1",
                             default_model="gpt-4o-mini", key_name="OPENAI_API_KEY").generate(
        _example(), cand("openai", "gpt-4o-mini"))
    assert captured["messages"][0] == {"role": "system", "content": "VARIANT-SYS-PROMPT"}

    GeminiProvider().generate(_example(), cand("gemini", "gemini-2.5-flash"))
    assert captured["systemInstruction"]["parts"][0]["text"] == "VARIANT-SYS-PROMPT"

    OllamaProvider().generate(_example(), cand("ollama", "llama3.2"))
    assert captured["messages"][0] == {"role": "system", "content": "VARIANT-SYS-PROMPT"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_providers_http.py::test_system_prompt_for_falls_back_to_task_default tests/unit/test_providers_http.py::test_providers_send_the_candidates_system_prompt -v`
Expected: FAIL — `ImportError: cannot import name 'system_prompt_for'` (and later `TypeError` for the unknown `system_prompt` kwarg on `Candidate`).

- [ ] **Step 3a: Add the field + model** — in `src/orionfold/domain/models.py`, change the `Candidate` class (currently ending at the `model` line) to add a field, and add a new `PromptVariant` model right after it:

```python
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
```

- [ ] **Step 3b: Add `system_prompt_for`** — in `src/orionfold/providers/http.py`, directly below the `TASK_SYSTEM_PROMPT` definition (after line 84), add:

```python
def system_prompt_for(candidate: "Candidate") -> str:
    """The system prompt for a run cell: the candidate's variant, else the global default."""
    return candidate.system_prompt or TASK_SYSTEM_PROMPT
```

And add the import at the top of `http.py` (it already imports from `orionfold.domain.models`):

```python
from orionfold.domain.models import Candidate, Privacy, ProviderResult
```

(Append `Candidate` to the existing `from orionfold.domain.models import Privacy, ProviderResult` line so the annotation resolves; drop the quotes around `"Candidate"` once imported.)

- [ ] **Step 3c: Thread it through the four providers.** In each provider's `generate`, replace the hardcoded `TASK_SYSTEM_PROMPT` with `system_prompt_for(candidate)`, and add `system_prompt_for` to the `from orionfold.providers.http import (...)` block:
  - `anthropic.py:44` → `"system": system_prompt_for(candidate),`
  - `openai_compatible.py:53` → `{"role": "system", "content": system_prompt_for(candidate)},`
  - `gemini.py:39` → `"systemInstruction": {"parts": [{"text": system_prompt_for(candidate)}]},`
  - `ollama.py:38` → `{"role": "system", "content": system_prompt_for(candidate)},`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_providers_http.py -v`
Expected: PASS (all, including the two new tests and the existing token-cap/redaction tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/domain/models.py src/orionfold/providers/ tests/unit/test_providers_http.py
git commit -m "feat(providers): per-candidate system prompt (system_prompt_for) threaded to all four providers

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `expand_prompt_variants` in the registry

**Files:**
- Modify: `src/orionfold/providers/registry.py` (append `_slug` + `expand_prompt_variants`)
- Test: `tests/unit/test_build_candidates.py` (append)

**Interfaces:**
- Consumes: `Candidate`, `PromptVariant` from `orionfold.domain.models`.
- Produces: `expand_prompt_variants(base: Candidate, variants: list[PromptVariant]) -> list[Candidate]`.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_build_candidates.py`:

```python
from orionfold.domain.models import PromptVariant
from orionfold.providers.registry import expand_prompt_variants


def test_expand_prompt_variants_mints_one_candidate_per_prompt():
    [base] = build_candidates(["mock_good"])  # model=None, bare mock
    variants = [
        PromptVariant(name="Baseline", system_prompt="Be neutral."),
        PromptVariant(name="Step by step", system_prompt="Think step by step."),
    ]
    out = expand_prompt_variants(base, variants)
    assert [c.id for c in out] == ["mock_good#baseline", "mock_good#step-by-step"]
    assert [c.label for c in out] == ["Baseline", "Step by step"]
    assert [c.system_prompt for c in out] == ["Be neutral.", "Think step by step."]
    # Provider/model/privacy copied from the base, so the engine routes + hashes correctly.
    assert all(c.provider_id == "mock_good" and c.model is None and c.privacy == "local" for c in out)


def test_expand_prompt_variants_dedupes_clashing_slugs():
    [base] = build_candidates(["ollama:llama3.2"])
    variants = [
        PromptVariant(name="Terse", system_prompt="a"),
        PromptVariant(name="terse!", system_prompt="b"),  # slugifies to the same "terse"
    ]
    out = expand_prompt_variants(base, variants)
    assert [c.id for c in out] == ["ollama:llama3.2#terse", "ollama:llama3.2#terse-2"]
    assert all(c.model == "llama3.2" and c.provider_id == "ollama" for c in out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_build_candidates.py -k expand -v`
Expected: FAIL — `ImportError: cannot import name 'expand_prompt_variants'`.

- [ ] **Step 3: Implement** — append to `src/orionfold/providers/registry.py` (and add `import re` near the top and `PromptVariant` to the `from orionfold.domain.models import Candidate` line → `import Candidate, PromptVariant`):

```python
def _slug(name: str) -> str:
    """Lowercase, alphanumeric-with-hyphens slug for a variant id segment."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "variant"


def expand_prompt_variants(
    base: Candidate, variants: list[PromptVariant]
) -> list[Candidate]:
    """Fan one model-bearing ``base`` candidate out into one candidate per prompt variant.

    Each variant becomes a candidate sharing ``base``'s provider/model/privacy but carrying its
    own ``system_prompt`` and a ``{base.id}#{slug}`` id. Slugs are deduped within the run so two
    same-named variants still get distinct ids (and distinct config_hash entries).
    """
    out: list[Candidate] = []
    seen: dict[str, int] = {}
    for v in variants:
        slug = _slug(v.name)
        seen[slug] = seen.get(slug, 0) + 1
        if seen[slug] > 1:
            slug = f"{slug}-{seen[slug]}"
        out.append(
            Candidate(
                id=f"{base.id}#{slug}",
                label=v.name,
                provider_id=base.provider_id,
                privacy=base.privacy,
                model=base.model,
                system_prompt=v.system_prompt,
            )
        )
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_build_candidates.py -v`
Expected: PASS (all, including the existing build_candidates tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/providers/registry.py tests/unit/test_build_candidates.py
git commit -m "feat(registry): expand_prompt_variants — fan one model into N prompt-variant candidates

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: `config_hash` includes `system_prompt` only when set

**Files:**
- Modify: `src/orionfold/proof/engine.py:47-55` (the candidates comprehension in `config_hash`)
- Test: `tests/unit/test_engine.py` (append)

**Interfaces:**
- Consumes: `config_hash(dataset, candidates, rubric)` (unchanged signature).

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_engine.py` (it already imports `config_hash`; add `Candidate` to its model imports if absent):

```python
def test_config_hash_unchanged_for_model_compare_runs():
    # A run whose candidates have system_prompt=None must hash identically to the pre-feature
    # payload — i.e. the system_prompt key must be ABSENT, not present-and-null. Lock the value.
    from orionfold.domain.models import Candidate, Dataset, Example, Rubric

    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    cands = [Candidate(id="mock_good", label="Mock", provider_id="mock_good")]
    import json, hashlib
    from orionfold import __version__
    payload = {
        "version": __version__,
        "dataset": {"id": ds.id, "examples": [e.model_dump() for e in ds.examples]},
        "candidates": [{"id": "mock_good", "provider_id": "mock_good", "privacy": "local", "model": None}],
        "rubric": Rubric(threshold=0.8).model_dump(),
    }
    expected = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    assert config_hash(ds, cands, Rubric(threshold=0.8)) == expected


def test_config_hash_distinguishes_prompt_variants():
    from orionfold.domain.models import Candidate, Dataset, Example, Rubric

    ds = Dataset(id="d1", name="d1", description="", examples=[Example(input_text="a", expected_text="b")])
    v1 = [Candidate(id="ollama#a", label="A", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    v2 = [Candidate(id="ollama#b", label="B", provider_id="ollama", model="llama3.2", system_prompt="verbose")]
    assert config_hash(ds, v1, Rubric()) != config_hash(ds, v2, Rubric())
    # Same prompts reproduce the same hash (repeatability).
    v1_again = [Candidate(id="ollama#a", label="A", provider_id="ollama", model="llama3.2", system_prompt="terse")]
    assert config_hash(ds, v1, Rubric()) == config_hash(ds, v1_again, Rubric())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_engine.py -k config_hash -v`
Expected: `test_config_hash_distinguishes_prompt_variants` FAILS (the two variant hashes are currently equal — `system_prompt` is ignored); `test_config_hash_unchanged_for_model_compare_runs` PASSES already (locks current behavior).

- [ ] **Step 3: Implement** — in `src/orionfold/proof/engine.py`, replace the `"candidates": [ ... ]` block inside `config_hash` (lines 47-55) with a conditional-key build:

```python
        "candidates": [
            _candidate_hash_fields(c)
            for c in candidates
        ],
```

and add this helper just above `config_hash`:

```python
def _candidate_hash_fields(c: Candidate) -> dict:
    fields = {"id": c.id, "provider_id": c.provider_id, "privacy": c.privacy, "model": c.model}
    # Add system_prompt ONLY when set, so model-compare runs (None) keep byte-identical hashes.
    if c.system_prompt is not None:
        fields["system_prompt"] = c.system_prompt
    return fields
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_engine.py -v`
Expected: PASS (all, including the existing determinism test).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/proof/engine.py tests/unit/test_engine.py
git commit -m "feat(engine): config_hash distinguishes prompt variants (conditional system_prompt, zero churn for model runs)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `RunRequest.prompt_variants` + server fan-out & validation (both endpoints)

**Files:**
- Modify: `src/orionfold/server/routes.py:66-70` (RunRequest), `:182-219` (`create_run`), `:227-315` (`create_run_stream`); add a shared `_resolve_candidates` helper.
- Modify: import `PromptVariant` + `expand_prompt_variants`.
- Test: `tests/integration/test_proof_api.py` (append)

**Interfaces:**
- Consumes: `build_candidates`, `expand_prompt_variants`, `PromptVariant`.
- Produces: `_resolve_candidates(body: RunRequest) -> list[Candidate]` raising `HTTPException` on bad input.

- [ ] **Step 1: Write the failing test** — append to `tests/integration/test_proof_api.py` (reuse its existing FastAPI test client + seeded-dataset fixtures; match the file's existing client/dataset-id helpers — inspect the top of the file for the exact fixture names and copy them):

```python
def test_prompt_variant_run_produces_one_entry_per_variant(client, sample_dataset_id):
    body = {
        "dataset_id": sample_dataset_id,
        "candidate_ids": ["mock_good"],
        "prompt_variants": [
            {"name": "Baseline", "system_prompt": "Be neutral."},
            {"name": "Concise", "system_prompt": "Be terse."},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    r = client.post("/api/runs", json=body)
    assert r.status_code == 200, r.text
    report = r.json()
    ids = [e["candidate_id"] for e in report["leaderboard"]]
    assert ids == ["mock_good#baseline", "mock_good#concise"]
    labels = sorted(e["label"] for e in report["leaderboard"])
    assert labels == ["Baseline", "Concise"]


def test_prompt_variant_run_rejects_multiple_models(client, sample_dataset_id):
    body = {
        "dataset_id": sample_dataset_id,
        "candidate_ids": ["mock_good", "mock_bad"],
        "prompt_variants": [
            {"name": "A", "system_prompt": "x"},
            {"name": "B", "system_prompt": "y"},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    assert client.post("/api/runs", json=body).status_code == 422


def test_prompt_variant_run_rejects_fewer_than_two(client, sample_dataset_id):
    body = {
        "dataset_id": sample_dataset_id,
        "candidate_ids": ["mock_good"],
        "prompt_variants": [{"name": "Only", "system_prompt": "x"}],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    assert client.post("/api/runs", json=body).status_code == 422


def test_prompt_variant_run_rejects_empty_fields(client, sample_dataset_id):
    body = {
        "dataset_id": sample_dataset_id,
        "candidate_ids": ["mock_good"],
        "prompt_variants": [
            {"name": "A", "system_prompt": "  "},
            {"name": "  ", "system_prompt": "y"},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    assert client.post("/api/runs", json=body).status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_proof_api.py -k prompt_variant -v`
Expected: FAIL — the happy-path returns 200 but with a single `mock_good` entry (no fan-out); the rejection tests get 200 instead of 422.

- [ ] **Step 3a: Add the request field** — in `src/orionfold/server/routes.py`, extend `RunRequest` (lines 66-70):

```python
class RunRequest(BaseModel):
    dataset_id: str
    candidate_ids: list[str]
    rubric: Rubric | None = None
    brief: ProofBrief
    prompt_variants: list[PromptVariant] | None = None
```

Update imports: add `PromptVariant` to the `from orionfold.domain.models import (...)` line, and add `expand_prompt_variants` to the `from orionfold.providers.registry import (...)` block.

- [ ] **Step 3b: Add the shared resolver** — add this helper above `create_run` (after the `_sse`/`init_db` helpers, near line 95):

```python
def _resolve_candidates(body: RunRequest) -> list[Candidate]:
    """Resolve the run's candidates, fanning out prompt variants when requested.

    Model-compare (no prompt_variants): today's behavior exactly. Prompt-compare: exactly one
    model, at least two non-empty variants, fanned out via expand_prompt_variants.
    """
    try:
        base = build_candidates(body.candidate_ids)
    except UnknownCandidateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not body.prompt_variants:
        return base
    if len(base) != 1:
        raise HTTPException(status_code=422, detail="Prompt comparison needs exactly one model.")
    variants = body.prompt_variants
    if len(variants) < 2:
        raise HTTPException(status_code=422, detail="Add at least two prompt variants to compare.")
    for v in variants:
        if not v.name.strip() or not v.system_prompt.strip():
            raise HTTPException(
                status_code=422, detail="Each prompt variant needs a name and prompt text."
            )
    return expand_prompt_variants(base[0], variants)
```

- [ ] **Step 3c: Use it in both endpoints.** In `create_run`, replace the block (lines 190-195):

```python
        if not body.candidate_ids:
            raise HTTPException(status_code=400, detail="Select at least one candidate")
        candidates = _resolve_candidates(body)
```

In `create_run_stream`, replace the block (lines 246-251):

```python
    if not body.candidate_ids:
        raise HTTPException(status_code=400, detail="Select at least one candidate")
    candidates = _resolve_candidates(body)
```

(Both endpoints keep their existing rubric/judge validation that follows.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_proof_api.py -v`
Expected: PASS (all, including the existing model-compare run tests).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/server/routes.py tests/integration/test_proof_api.py
git commit -m "feat(api): RunRequest.prompt_variants — fan one model into N prompts (validated 422s) in both run endpoints

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `LeaderboardEntry.system_prompt` (provenance carrier)

**Files:**
- Modify: `src/orionfold/domain/models.py:98-114` (LeaderboardEntry)
- Modify: `src/orionfold/proof/leaderboard.py:32-48` (entry construction)
- Test: `tests/unit/test_leaderboard.py` (append)

**Interfaces:**
- Produces: `LeaderboardEntry.system_prompt: str | None = None`, populated from `cand.system_prompt`.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_leaderboard.py` (match its existing helpers for building candidates + result rows; inspect the top of the file):

```python
def test_leaderboard_entry_carries_candidate_system_prompt():
    from orionfold.domain.models import Candidate, ResultRow
    from orionfold.proof.leaderboard import build_leaderboard

    cand = Candidate(id="ollama#terse", label="Terse", provider_id="ollama",
                     model="llama3.2", system_prompt="Be terse.")
    rows = [ResultRow(candidate_id="ollama#terse", example_index=0, input_text="a",
                      expected_text="b", output_text="b", score=1.0, passed=True,
                      latency_ms=10, estimated_cost_usd=0.0, privacy="local", error=None)]
    [entry] = build_leaderboard([cand], rows)
    assert entry.system_prompt == "Be terse."


def test_leaderboard_entry_system_prompt_none_for_model_compare():
    from orionfold.domain.models import Candidate, ResultRow
    from orionfold.proof.leaderboard import build_leaderboard

    cand = Candidate(id="mock_good", label="Mock", provider_id="mock_good")
    rows = [ResultRow(candidate_id="mock_good", example_index=0, input_text="a",
                      expected_text="b", output_text="b", score=1.0, passed=True,
                      latency_ms=10, estimated_cost_usd=0.0, privacy="local", error=None)]
    [entry] = build_leaderboard([cand], rows)
    assert entry.system_prompt is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_leaderboard.py -k system_prompt -v`
Expected: FAIL — `AttributeError`/validation: `LeaderboardEntry` has no `system_prompt`.

- [ ] **Step 3a: Add the field** — in `src/orionfold/domain/models.py`, add to `LeaderboardEntry` (after the `model` line, before `total`):

```python
    system_prompt: str | None = None  # set for prompt-variant entries; None for model-compare
```

- [ ] **Step 3b: Populate it** — in `src/orionfold/proof/leaderboard.py`, add `system_prompt=cand.system_prompt,` to the `LeaderboardEntry(...)` constructor (right after `model=cand.model,`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_leaderboard.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add src/orionfold/domain/models.py src/orionfold/proof/leaderboard.py tests/unit/test_leaderboard.py
git commit -m "feat(leaderboard): carry the candidate's system_prompt on each entry (receipt provenance)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: Receipt v6 — prompt-variants section, JSON field, honest repro; regenerate samples

**Files:**
- Modify: `src/orionfold/receipts/export.py` (RECEIPT_VERSION, `build_receipt`, `to_markdown`, `to_html`)
- Modify: `tests/unit/test_receipts.py:126-127`, `tests/unit/test_receipt_no_winner.py:66,116` (re-pin version)
- Test: `tests/unit/test_receipts.py` (append a prompt-variants test)
- Regenerate: `scripts/gen_samples.py` output

**Interfaces:**
- Consumes: `LeaderboardEntry.system_prompt` (Task 5); `run.candidates` carry `system_prompt`.
- Produces: receipt `prompt_variants: list[{name, system_prompt}]` (empty for model-compare); `RECEIPT_VERSION == 6`.

- [ ] **Step 1: Write the failing test** — append to `tests/unit/test_receipts.py` (reuse its existing report-builder helper; inspect the top of the file for it, e.g. `_report(...)`):

```python
def test_receipt_records_prompt_variants_and_text():
    from orionfold.domain.models import (
        Candidate, LeaderboardEntry, ProofBrief, ProofReport, ProofRun, ResultRow,
        Rubric, RunCostSummary,
    )

    cands = [
        Candidate(id="mock_good#baseline", label="Baseline", provider_id="mock_good",
                  system_prompt="Be neutral."),
        Candidate(id="mock_good#concise", label="Concise", provider_id="mock_good",
                  system_prompt="Be terse."),
    ]
    run = ProofRun(
        id="run_x", brief=ProofBrief(task_name="t", decision_question="q"),
        dataset_id="d1", dataset_name="D1", rubric=Rubric(threshold=0.8),
        candidates=cands, config_hash="abc123abc123", created_at="2026-06-21T00:00:00Z",
    )
    lb = [
        LeaderboardEntry(candidate_id="mock_good#baseline", label="Baseline",
                         provider_id="mock_good", privacy="local", system_prompt="Be neutral.",
                         total=1, pass_count=1, pass_rate=1.0, avg_score=1.0, avg_latency_ms=10,
                         total_estimated_cost_usd=0.0, failure_count=0, error_count=0,
                         recommended=True),
        LeaderboardEntry(candidate_id="mock_good#concise", label="Concise",
                         provider_id="mock_good", privacy="local", system_prompt="Be terse.",
                         total=1, pass_count=1, pass_rate=1.0, avg_score=1.0, avg_latency_ms=10,
                         total_estimated_cost_usd=0.0, failure_count=0, error_count=0),
    ]
    report = ProofReport(run=run, leaderboard=lb, results=[],
                         cost_summary=RunCostSummary(candidate_cost_usd=0, judge_cost_usd=0, total_cost_usd=0))

    data = export.build_receipt(report)
    assert data["receipt_version"] == 6
    assert data["prompt_variants"] == [
        {"name": "Baseline", "system_prompt": "Be neutral."},
        {"name": "Concise", "system_prompt": "Be terse."},
    ]
    md = export.to_markdown(report)
    assert "## Prompt variants" in md
    assert "Be neutral." in md and "Be terse." in md
    html = export.to_html(report)
    assert "Prompt variants" in html and "Be terse." in html
    # Provenance, not secrets: nothing key-shaped leaks (sanity).
    assert "API_KEY" not in md and "API_KEY" not in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_receipts.py -k prompt_variants -v`
Expected: FAIL — `data["receipt_version"]` is 5 and `prompt_variants` key is absent.

- [ ] **Step 3a: Bump version + add the data** — in `src/orionfold/receipts/export.py`, change `RECEIPT_VERSION = 5` to `6` and add a comment line to the version log:

```python
# v6: prompt-variant runs — each leaderboard entry carries its system_prompt; the receipt adds a
# "Prompt variants" section (name + full prompt text) for provenance. Empty for model-compare runs.
RECEIPT_VERSION = 6
```

In `build_receipt`, add a `prompt_variants` list to the returned dict (after `"leaderboard": [...]`):

```python
        "prompt_variants": [
            {"name": e["label"], "system_prompt": e["system_prompt"]}
            for e in (entry.model_dump() for entry in report.leaderboard)
            if e.get("system_prompt")
        ],
```

(Compute it once before the return if you prefer; keep it a plain list of `{name, system_prompt}`.)

- [ ] **Step 3b: Make the repro honest.** In `build_receipt`, the `repro` block currently emits a model-compare `rerun`. Make it reflect prompt variants when present. Replace the `"repro": { ... }` block with:

```python
        "repro": {
            "run_id": run.id,
            "config_hash": run.config_hash,
            "created_at": run.created_at,
            "dataset_id": run.dataset_id,
            "candidate_ids": candidate_ids,
            "rubric": run.rubric.model_dump(),
            "rerun": _rerun_command(run),
        },
```

and add this helper above `build_receipt`:

```python
def _rerun_command(run) -> str:
    """The POST body that reproduces this run — prompt-variant shape when variants are present."""
    variants = [
        {"name": c.label, "system_prompt": c.system_prompt}
        for c in run.candidates
        if c.system_prompt is not None
    ]
    if variants:
        model_id = run.candidates[0].id.split("#", 1)[0]
        body = {"dataset_id": run.dataset_id, "candidate_ids": [model_id], "prompt_variants": variants}
    else:
        body = {"dataset_id": run.dataset_id, "candidate_ids": [c.id for c in run.candidates]}
    return "POST /api/runs " + json.dumps(body, ensure_ascii=False)
```

- [ ] **Step 3c: Render the Markdown section.** In `to_markdown`, after the failure-cases block and before the `## Repro` block, insert:

```python
    variants = data["prompt_variants"]
    if variants:
        lines += ["", "## Prompt variants", "",
                  f"_Same model, {len(variants)} system prompts compared._", ""]
        for v in variants:
            lines += [f"- **{_md_inline(v['name'])}:** {_md_inline(v['system_prompt'])}"]
```

- [ ] **Step 3d: Render the HTML section.** In `to_html`, build a variants block and inject it before the `<h2>Repro</h2>` line. Add, just before the `return f"""..."""`:

```python
    variants = data["prompt_variants"]
    if variants:
        items = "".join(
            f"<li><strong>{html.escape(v['name'])}:</strong> {html.escape(v['system_prompt'])}</li>"
            for v in variants
        )
        variants_html = f"<h2>Prompt variants</h2><ul class='variants'>{items}</ul>"
    else:
        variants_html = ""
```

and insert `{variants_html}` into the template immediately before `  <h2>Repro</h2>`.

- [ ] **Step 3e: Re-pin the version assertions.** Change `tests/unit/test_receipts.py:127` `assert export.RECEIPT_VERSION == 5` → `== 6`, and `tests/unit/test_receipt_no_winner.py` lines 66 + 116 `data["receipt_version"] == 5` → `== 6`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_receipts.py tests/unit/test_receipt_no_winner.py -v`
Expected: PASS (all).

- [ ] **Step 5: Regenerate sample receipts + commit**

Run: `uv run python scripts/gen_samples.py` (model-compare samples are unchanged in structure; their `receipt_version` flips to 6 and `prompt_variants` is `[]`).

```bash
git add src/orionfold/receipts/export.py tests/unit/test_receipts.py tests/unit/test_receipt_no_winner.py docs/samples/ samples/ 2>/dev/null; git add -A
git commit -m "feat(receipts): RECEIPT_VERSION 6 — prompt-variants section + honest prompt-variant repro; regen samples

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

(Confirm the sample-receipt output directory with `grep _OUT scripts/gen_samples.py` and stage that path.)

---

### Task 7: Frontend API types — `prompt_variants` + schema fields

**Files:**
- Modify: `web/src/lib/api.ts:8-14` (candidateSchema), `:77-93` (leaderboardEntrySchema), `:269-274` (RunRequest)
- Test: covered by Task 8/9 component tests (api.ts has no standalone unit test file).

**Interfaces:**
- Produces: `PromptVariant` TS type `{ name: string; system_prompt: string }`; `RunRequest.prompt_variants?: PromptVariant[]`; `candidateSchema`/`leaderboardEntrySchema` gain optional `system_prompt`.

- [ ] **Step 1: Add the schema fields.** In `web/src/lib/api.ts`:
  - In `candidateSchema` (after `model:`): `system_prompt: z.string().nullable().optional(),`
  - In `leaderboardEntrySchema` (after `model:`): `system_prompt: z.string().nullable().optional(),`
  - Add a `PromptVariant` type and extend `RunRequest`:

```typescript
export interface PromptVariant {
  name: string;
  system_prompt: string;
}

export interface RunRequest {
  dataset_id: string;
  candidate_ids: string[];
  rubric?: z.infer<typeof rubricSchema> | null;
  brief: ProofBrief;
  prompt_variants?: PromptVariant[];
}
```

- [ ] **Step 2: Verify it compiles**

Run: `pnpm --dir web build`
Expected: clean `tsc --noEmit && vite build` (no type errors).

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/api.ts
git commit -m "feat(web/api): PromptVariant type + RunRequest.prompt_variants + system_prompt schema fields

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Frontend pure helpers — `promptVariants.ts`

**Files:**
- Create: `web/src/features/proof/promptVariants.ts`
- Test: `web/src/features/proof/promptVariants.test.ts`

**Interfaces:**
- Consumes: `SelectionPanel`, `PromptVariant` from `../../lib/api`.
- Produces: `STARTER_VARIANTS: PromptVariant[]`; `validPromptVariants(vs): boolean`; `cleanVariants(vs): PromptVariant[]`; `flattenModels(panel): ModelOption[]`; `defaultPromptModel(panel): string`.

- [ ] **Step 1: Write the failing test** — create `web/src/features/proof/promptVariants.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import type { SelectionPanel } from "../../lib/api";
import {
  STARTER_VARIANTS, validPromptVariants, cleanVariants, flattenModels, defaultPromptModel,
} from "./promptVariants";

const panel: SelectionPanel = {
  providers: [
    { provider_id: "mock_good", label: "Mock · good", privacy: "local", available: true,
      supports_custom: false, candidate_id: "mock_good", models: [] },
    { provider_id: "anthropic", label: "Anthropic", privacy: "cloud", available: false,
      supports_custom: true, candidate_id: null, models: [
        { candidate_id: "anthropic:claude-haiku-4-5", model: "claude-haiku-4-5",
          display_name: "Claude Haiku 4.5", tier: "balanced", cost_class: "$",
          context_window: null, latest: false, recommended: true } ] },
  ],
};

describe("promptVariants helpers", () => {
  it("ships two starter variants", () => {
    expect(STARTER_VARIANTS).toHaveLength(2);
    expect(STARTER_VARIANTS[0].name).toBe("Baseline");
  });

  it("requires two non-empty variants to be valid", () => {
    expect(validPromptVariants([{ name: "A", system_prompt: "x" }])).toBe(false);
    expect(validPromptVariants([{ name: "A", system_prompt: "x" }, { name: "B", system_prompt: " " }])).toBe(false);
    expect(validPromptVariants([{ name: "A", system_prompt: "x" }, { name: "B", system_prompt: "y" }])).toBe(true);
  });

  it("cleans out blank rows and trims", () => {
    expect(cleanVariants([{ name: " A ", system_prompt: " x " }, { name: "", system_prompt: "y" }]))
      .toEqual([{ name: "A", system_prompt: "x" }]);
  });

  it("flattens mocks + catalog models, carrying availability", () => {
    const opts = flattenModels(panel);
    expect(opts).toEqual([
      { candidateId: "mock_good", label: "Mock · good", available: true },
      { candidateId: "anthropic:claude-haiku-4-5", label: "Anthropic · Claude Haiku 4.5", available: false },
    ]);
  });

  it("defaults the prompt model to the first available option", () => {
    expect(defaultPromptModel(panel)).toBe("mock_good");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run promptVariants`
Expected: FAIL — module `./promptVariants` not found.

- [ ] **Step 3: Implement** — create `web/src/features/proof/promptVariants.ts`:

```typescript
// Pure helpers for the "one model, N prompts" compare mode. No React, no network.
import type { PromptVariant, SelectionPanel } from "../../lib/api";

// Starter prompts the editor seeds so the first run is an edit, not a blank page. "Baseline"
// mirrors the server's TASK_SYSTEM_PROMPT so a variant run can include the current default.
export const STARTER_VARIANTS: PromptVariant[] = [
  {
    name: "Baseline",
    system_prompt:
      "Complete the task implied by the input. Respond with only the result — no preamble, labels, or explanation.",
  },
  {
    name: "Concise",
    system_prompt: "Answer in as few words as possible. Output only the essential result.",
  },
];

// A comparison needs at least two complete (name + prompt) variants.
export function validPromptVariants(vs: PromptVariant[]): boolean {
  return cleanVariants(vs).length >= 2;
}

// Trim and drop rows missing a name or prompt — the exact list the run request should carry.
export function cleanVariants(vs: PromptVariant[]): PromptVariant[] {
  return vs
    .map((v) => ({ name: v.name.trim(), system_prompt: v.system_prompt.trim() }))
    .filter((v) => v.name && v.system_prompt);
}

export interface ModelOption {
  candidateId: string;
  label: string;
  available: boolean;
}

// One selectable model per row: mocks (group candidate_id) + each catalog model.
export function flattenModels(panel: SelectionPanel | undefined): ModelOption[] {
  const out: ModelOption[] = [];
  for (const g of panel?.providers ?? []) {
    if (g.candidate_id) out.push({ candidateId: g.candidate_id, label: g.label, available: g.available });
    for (const m of g.models) {
      out.push({
        candidateId: m.candidate_id,
        label: `${g.label} · ${m.display_name}`,
        available: g.available,
      });
    }
  }
  return out;
}

// Prefer the first AVAILABLE option (keyless mocks come first) so prompt-compare runs keyless.
export function defaultPromptModel(panel: SelectionPanel | undefined): string {
  const opts = flattenModels(panel);
  return (opts.find((o) => o.available) ?? opts[0])?.candidateId ?? "";
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test --run promptVariants`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/promptVariants.ts web/src/features/proof/promptVariants.test.ts
git commit -m "feat(web): promptVariants pure helpers (starter prompts, validation, model flatten)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Frontend `PromptVariants` editor + `Compare by` toggle component

**Files:**
- Create: `web/src/features/proof/PromptVariants.tsx`
- Test: `web/src/features/proof/PromptVariants.test.tsx`

**Interfaces:**
- Consumes: `PromptVariant` type; `flattenModels`, `ModelOption` from `./promptVariants`.
- Produces: `<PromptVariants variants modelId panel onChangeVariants onChangeModel />` rendering a single-model `<select>` (aria-label "Prompt model") + add/remove name+textarea rows.

- [ ] **Step 1: Write the failing test** — create `web/src/features/proof/PromptVariants.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { SelectionPanel } from "../../lib/api";
import { PromptVariants } from "./PromptVariants";

const panel: SelectionPanel = {
  providers: [
    { provider_id: "mock_good", label: "Mock · good", privacy: "local", available: true,
      supports_custom: false, candidate_id: "mock_good", models: [] },
  ],
};
const variants = [
  { name: "Baseline", system_prompt: "a" },
  { name: "Concise", system_prompt: "b" },
];

describe("PromptVariants", () => {
  it("renders the model select and a row per variant", () => {
    render(<PromptVariants variants={variants} modelId="mock_good" panel={panel}
      onChangeVariants={() => {}} onChangeModel={() => {}} />);
    expect(screen.getByLabelText(/Prompt model/i)).toBeInTheDocument();
    expect(screen.getAllByRole("textbox", { name: /variant prompt/i })).toHaveLength(2);
  });

  it("adds a variant row", () => {
    const onChange = vi.fn();
    render(<PromptVariants variants={variants} modelId="mock_good" panel={panel}
      onChangeVariants={onChange} onChangeModel={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /add prompt/i }));
    expect(onChange).toHaveBeenCalledWith([...variants, { name: "", system_prompt: "" }]);
  });

  it("removes a variant row", () => {
    const onChange = vi.fn();
    render(<PromptVariants variants={variants} modelId="mock_good" panel={panel}
      onChangeVariants={onChange} onChangeModel={() => {}} />);
    fireEvent.click(screen.getAllByRole("button", { name: /remove/i })[0]);
    expect(onChange).toHaveBeenCalledWith([variants[1]]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run PromptVariants`
Expected: FAIL — module `./PromptVariants` not found.

- [ ] **Step 3: Implement** — create `web/src/features/proof/PromptVariants.tsx`:

```tsx
import { Plus, X } from "lucide-react";
import type { PromptVariant, SelectionPanel } from "../../lib/api";
import { flattenModels } from "./promptVariants";

const inputCls =
  "rounded-lg border border-(--color-panel-line) bg-(--color-panel) px-3 py-2 text-(--color-ink)";

export interface PromptVariantsProps {
  variants: PromptVariant[];
  modelId: string;
  panel: SelectionPanel;
  onChangeVariants: (next: PromptVariant[]) => void;
  onChangeModel: (id: string) => void;
}

// "One model, N prompts": pick a single model, then author named system-prompt variants. The
// model is fixed so the leaderboard isolates which wording wins.
export function PromptVariants(props: PromptVariantsProps) {
  const { variants, modelId, panel, onChangeVariants, onChangeModel } = props;
  const models = flattenModels(panel);

  const update = (i: number, patch: Partial<PromptVariant>) =>
    onChangeVariants(variants.map((v, idx) => (idx === i ? { ...v, ...patch } : v)));
  const add = () => onChangeVariants([...variants, { name: "", system_prompt: "" }]);
  const remove = (i: number) => onChangeVariants(variants.filter((_, idx) => idx !== i));

  return (
    <fieldset className="grid gap-4">
      <legend className="text-sm text-(--color-ink-muted)">Prompt variants</legend>

      <label className="grid gap-1.5 text-sm">
        <span className="text-(--color-ink-muted)">Prompt model</span>
        <select
          aria-label="Prompt model"
          value={modelId}
          onChange={(e) => onChangeModel(e.target.value)}
          className={inputCls}
        >
          {models.map((m) => (
            <option key={m.candidateId} value={m.candidateId} disabled={!m.available}>
              {m.label}
              {m.available ? "" : " (add a key)"}
            </option>
          ))}
        </select>
        <span className="text-xs text-(--color-ink-faint)">
          The single model every prompt variant is compared on.
        </span>
      </label>

      <div className="grid gap-3">
        {variants.map((v, i) => (
          <div key={i} className="grid gap-2 rounded-lg border border-(--color-panel-line) p-3">
            <div className="flex items-center gap-2">
              <input
                aria-label={`Variant name ${i + 1}`}
                value={v.name}
                placeholder="Name (e.g. Terse)"
                onChange={(e) => update(i, { name: e.target.value })}
                className={inputCls + " flex-1"}
              />
              <button
                type="button"
                aria-label={`Remove variant ${i + 1}`}
                onClick={() => remove(i)}
                disabled={variants.length <= 2}
                className="rounded-lg p-2 text-(--color-ink-muted) hover:text-(--color-ink) disabled:opacity-40"
              >
                <X aria-hidden className="h-4 w-4" />
              </button>
            </div>
            <textarea
              aria-label={`Variant prompt ${i + 1}`}
              value={v.system_prompt}
              placeholder="System prompt for this variant…"
              rows={3}
              onChange={(e) => update(i, { system_prompt: e.target.value })}
              className={inputCls}
            />
          </div>
        ))}
      </div>

      <div>
        <button
          type="button"
          onClick={add}
          className="flex items-center gap-1.5 rounded-lg border border-(--color-panel-line) px-3 py-2 text-sm text-(--color-ink-muted) hover:text-(--color-ink)"
        >
          <Plus aria-hidden className="h-4 w-4" /> Add prompt
        </button>
      </div>
    </fieldset>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pnpm --dir web test --run PromptVariants`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/PromptVariants.tsx web/src/features/proof/PromptVariants.test.tsx
git commit -m "feat(web): PromptVariants editor — single-model select + add/remove named prompt rows

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Wire the `Compare by` toggle into RunSetup + ProofCockpit

**Files:**
- Modify: `web/src/features/proof/RunSetup.tsx` (toggle + conditional render + canRun)
- Modify: `web/src/features/proof/ProofCockpit.tsx` (state + run-request building)
- Test: `web/src/features/proof/RunSetup.test.tsx` (append)

**Interfaces:**
- Consumes: `PromptVariants` (Task 9); `validPromptVariants`, `STARTER_VARIANTS`, `defaultPromptModel` (Task 8); `PromptVariant` type.
- Produces: RunSetup props `compareBy: "models" | "prompts"`, `onCompareByChange`, `promptVariants`, `onPromptVariantsChange`, `promptModel`, `onPromptModelChange`.

- [ ] **Step 1: Write the failing test** — append to `web/src/features/proof/RunSetup.test.tsx` (reuse the file's existing render helper / default props; inspect the top of the file and copy its pattern, passing the new props):

```tsx
it("shows the prompt editor when Compare by Prompts is selected", () => {
  renderRunSetup({ compareBy: "prompts" }); // helper passes through to RunSetup props
  expect(screen.getByLabelText(/Prompt model/i)).toBeInTheDocument();
  // The model picker (Models mode) is hidden in Prompts mode.
  expect(screen.queryByText(/^Candidates$/)).not.toBeInTheDocument();
});

it("disables Run until two prompt variants are complete", () => {
  renderRunSetup({
    compareBy: "prompts",
    promptVariants: [{ name: "A", system_prompt: "x" }, { name: "B", system_prompt: "" }],
    brief: { task_name: "t", decision_question: "q", success_criteria: "" },
  });
  expect(screen.getByRole("button", { name: /Run proof/ })).toBeDisabled();
});
```

(If `RunSetup.test.tsx` has no `renderRunSetup` helper, add a small one that builds the full default prop set — including `compareBy: "models"`, `promptVariants: STARTER_VARIANTS`, `promptModel: "mock_good"`, and no-op handlers — and shallow-merges the override object.)

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm --dir web test --run RunSetup`
Expected: FAIL — RunSetup doesn't accept `compareBy` / renders the picker regardless.

- [ ] **Step 3a: Extend RunSetup.** In `web/src/features/proof/RunSetup.tsx`:
  - Import: `import { PromptVariants } from "./PromptVariants";` and `import type { PromptVariant } from "../../lib/api";` and `import { validPromptVariants } from "./promptVariants";`
  - Add to `RunSetupProps`:

```typescript
  compareBy: "models" | "prompts";
  onCompareByChange: (mode: "models" | "prompts") => void;
  promptVariants: PromptVariant[];
  onPromptVariantsChange: (next: PromptVariant[]) => void;
  promptModel: string;
  onPromptModelChange: (id: string) => void;
```

  - Destructure them in the component body.
  - Replace `const canRun = selectedCandidates.length > 0 && brief.task_name.trim().length > 0;` with:

```typescript
  const canRun =
    brief.task_name.trim().length > 0 &&
    (compareBy === "prompts"
      ? Boolean(promptModel) && validPromptVariants(promptVariants)
      : selectedCandidates.length > 0);
```

  - Replace the `<CandidatePicker ... />` block (lines 77-81) with a toggle + conditional render:

```tsx
        <div className="grid gap-3">
          <div role="group" aria-label="Compare by" className="inline-flex w-fit rounded-lg border border-(--color-panel-line) p-0.5 text-sm">
            {(["models", "prompts"] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={compareBy === mode}
                onClick={() => onCompareByChange(mode)}
                className={
                  "rounded-md px-3 py-1.5 capitalize transition-colors " +
                  (compareBy === mode
                    ? "bg-(--color-accent-strong) text-(--color-accent-ink)"
                    : "text-(--color-ink-muted) hover:text-(--color-ink)")
                }
              >
                {mode}
              </button>
            ))}
          </div>

          {compareBy === "prompts" ? (
            <PromptVariants
              variants={promptVariants}
              modelId={promptModel}
              panel={panel}
              onChangeVariants={onPromptVariantsChange}
              onChangeModel={onPromptModelChange}
            />
          ) : (
            <CandidatePicker panel={panel} selected={selectedCandidates} onToggle={onToggleCandidate} />
          )}
        </div>
```

- [ ] **Step 3b: Wire ProofCockpit.** In `web/src/features/proof/ProofCockpit.tsx`:
  - Import the helpers + type: `import { STARTER_VARIANTS, cleanVariants, defaultPromptModel } from "./promptVariants";` and add `type PromptVariant` to the `../../lib/api` import.
  - Add state (near the other `useState`s, ~line 60):

```tsx
  const [compareBy, setCompareBy] = useState<"models" | "prompts">("models");
  const [promptVariants, setPromptVariants] = useState<PromptVariant[]>(STARTER_VARIANTS);
  const [promptModel, setPromptModel] = useState("");
  const resolvedPromptModel = promptModel || defaultPromptModel(selection.data);
```

  - Pass the new props to `<RunSetup>`:

```tsx
          compareBy={compareBy}
          onCompareByChange={setCompareBy}
          promptVariants={promptVariants}
          onPromptVariantsChange={setPromptVariants}
          promptModel={resolvedPromptModel}
          onPromptModelChange={setPromptModel}
```

  - Replace the `onRun` mutate body so Prompts mode sends one model + variants:

```tsx
          onRun={() =>
            runMutation.mutate(
              compareBy === "prompts"
                ? {
                    dataset_id: resolvedDatasetId,
                    candidate_ids: [resolvedPromptModel],
                    prompt_variants: cleanVariants(promptVariants),
                    brief: effectiveBrief,
                    ...(rubric ? { rubric } : {}),
                  }
                : {
                    dataset_id: resolvedDatasetId,
                    candidate_ids: resolvedSelected,
                    brief: effectiveBrief,
                    ...(rubric ? { rubric } : {}),
                  },
            )
          }
```

- [ ] **Step 4: Run tests + build to verify**

Run: `pnpm --dir web test --run && pnpm --dir web build`
Expected: PASS (all Vitest, including RunSetup + ProofCockpit), clean build.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/proof/RunSetup.tsx web/src/features/proof/ProofCockpit.tsx web/src/features/proof/RunSetup.test.tsx
git commit -m "feat(web): Compare by Models|Prompts toggle wired into RunSetup + ProofCockpit run request

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: e2e — keyless prompt-compare flow

**Files:**
- Modify: `e2e/playwright/proof.spec.ts` (append a test)

**Interfaces:**
- Consumes: the full wired UI + API (Tasks 1-10).

- [ ] **Step 1: Write the test** — append to `e2e/playwright/proof.spec.ts`:

```typescript
test("prompt compare: one model, two prompts → leaderboard + receipt section", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Orionfold Proof" })).toBeVisible();

  // Switch the comparison axis to Prompts.
  await page.getByRole("button", { name: "prompts", exact: true }).click();

  // The prompt editor appears, seeded with two starter variants on a keyless mock model.
  await expect(page.getByLabel(/Prompt model/i)).toBeVisible();
  await expect(page.getByLabel(/Variant prompt 1/i)).toBeVisible();
  await expect(page.getByLabel(/Variant prompt 2/i)).toBeVisible();

  // Run keyless (mock model) and confirm a leaderboard row per variant.
  await page.getByRole("button", { name: /Run proof/ }).click();
  const leaderboard = page.getByRole("region", { name: "Leaderboard" });
  await expect(leaderboard).toBeVisible();
  await expect(leaderboard.getByText("Baseline")).toBeVisible();
  await expect(leaderboard.getByText("Concise")).toBeVisible();

  // The receipt records the prompt variants (open it from the archive).
  await page.getByRole("button", { name: "Receipts" }).click();
  await page.getByRole("button", { name: /Which model should I trust|Investment memo/i }).first().click();
  const frame = page.frameLocator('iframe[title="Proof Receipt preview"]');
  await expect(frame.getByText("Prompt variants")).toBeVisible();
});
```

(If the receipt iframe assertion proves brittle in the harness, fall back to fetching the JSON receipt via `page.request.get` for the latest run and asserting `prompt_variants.length === 2` — keep whichever the harness runs green.)

- [ ] **Step 2: Rebuild the embed, then run e2e**

Run: `bash scripts/build.sh && pnpm --dir web e2e`
Expected: PASS — the new test plus the existing 5 (rebuild is REQUIRED; `orionfold up` serves the embedded cockpit, not vite).

- [ ] **Step 3: Commit**

```bash
git add e2e/playwright/proof.spec.ts
git commit -m "test(e2e): keyless prompt-compare flow — toggle, two prompts, leaderboard rows, receipt section

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Docs — CHANGELOG, demo note, full verify sweep

**Files:**
- Modify: `CHANGELOG.md` ([Unreleased])
- Modify: `docs/demo-script.md` (a one-line prompt-compare note, if natural)

- [ ] **Step 1: Update CHANGELOG.** Add under `[Unreleased]`:

```markdown
### Added
- **Prompt-variant candidates (#6).** A `Compare by: Models | Prompts` toggle compares one
  model across N named system prompts in a single run. Each prompt becomes a leaderboard row;
  the receipt records every variant's full prompt text for provenance (RECEIPT_VERSION 6).
  Keyless: a prompt-compare run on a mock exercises the full path without API keys.
```

- [ ] **Step 2: Full verify sweep** (the Global Constraints gate):

```bash
uv run pytest -q
uv run ruff check src tests
pnpm --dir web test --run
pnpm --dir web build
bash scripts/build.sh && pnpm --dir web e2e
```

Expected: all green. (Restart any running `orionfold up` after backend changes; the e2e rebuilds the embed itself in the command above.)

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md docs/demo-script.md
git commit -m "docs: changelog + demo note for prompt-variant candidates (#6)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage** — every spec section maps to a task:
- Data model (`Candidate.system_prompt`, `PromptVariant`) → Task 1. Identity (`#slug` + dedup) → Task 2. API (`prompt_variants`, fan-out, 422s) → Task 4. Provider threading → Task 1. `config_hash` conditional → Task 3. Receipt v6 + provenance + repro → Task 6 (leaderboard carrier → Task 5). Frontend toggle/editor/select/wiring → Tasks 7-10. Testing → every task + e2e Task 11. Keyless invariant → Tasks 4 (mock fan-out), 8 (`defaultPromptModel` prefers available), 11 (keyless e2e). Sample regen → Task 6.

**2. Placeholder scan** — no TBD/TODO; every code step shows real code; two spots intentionally say "inspect the top of the file and copy the existing fixture/helper" (integration client fixtures in Task 4, report/leaderboard builders in Tasks 5-6, RunSetup render helper in Task 10) because those helpers already exist and must be reused verbatim rather than re-invented — that is a reuse instruction, not a placeholder.

**3. Type consistency** — `system_prompt` is `str | None` on `Candidate` and `LeaderboardEntry`, optional+nullable in Zod. `PromptVariant` is `{name, system_prompt}` in Python (Pydantic), TS (interface), and Zod-free request type. `expand_prompt_variants(base, variants)`, `system_prompt_for(candidate)`, `_resolve_candidates(body)`, `flattenModels`/`defaultPromptModel`/`cleanVariants`/`validPromptVariants`/`STARTER_VARIANTS` names match across all tasks that consume them. Receipt key is `prompt_variants` everywhere.

## Notes carried from the HANDOFF (read before executing)
- The harness emits STALE TS diagnostics mid-edit (false "cannot find module"). Trust `pnpm --dir web build` + the real test runs, not the inline diagnostics.
- The e2e uses a fresh DB; a stale local server/DB can cause a false failure — kill the port + delete `/tmp/orionfold-e2e.db`, rebuild the embed, re-run.
- A sibling `orionfold-proof-codex` checkout runs its own servers (8787/5173). For any manual browser check bind a provably-free port and assert the listener PID is yours; `vite.config.ts` honors `VITE_DEV_PORT` / `VITE_API_PROXY`.
- create-dataset route field is `text` (not `content`).
