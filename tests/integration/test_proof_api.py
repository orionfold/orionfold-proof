"""End-to-end API loop over a temp DB — runs fully keyless (no providers, no network)."""

import json

import pytest
from fastapi.testclient import TestClient

from orionfold.catalog.models import ModelCatalog
from orionfold.server.app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(db_path=tmp_path / "proof.db")
    with TestClient(app) as c:  # triggers lifespan: migrate + seed
        yield c


def test_datasets_and_candidates_are_available(client, tmp_path, monkeypatch):
    # Hermetic: no ambient provider keys and no .env.local, so the listing is the local-only
    # set regardless of the developer's shell.
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", str(tmp_path / "absent.env"))
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    datasets = client.get("/api/datasets").json()
    assert any(d["id"] == "investment-memo-summarization" for d in datasets)
    candidate_ids = {c["provider_id"] for c in client.get("/api/candidates").json()}
    # Mocks + local profiles are always offered; cloud profiles are absent without keys.
    assert candidate_ids == {"mock_good", "mock_bad", "ollama", "lmstudio"}


def test_bundled_bench_dataset_is_listed_with_corpus_after_startup(client):
    """The bench dataset auto-seeds at startup so it's selectable in the cockpit out of the box,
    carrying its corpus binding (what makes the Governance bench card surface)."""
    datasets = client.get("/api/datasets").json()
    bench = next((d for d in datasets if d["id"] == "advisor-curveball-v0.2"), None)
    assert bench is not None, "advisor-curveball-v0.2 not listed after startup"
    assert bench["corpus_id"] == "ainative-field-notes"
    # Non-sample on purpose: survives "remove samples" and never hijacks the guided-demo's
    # find(is_sample) target nor the demo-judge auto-default (both keyed on is_sample).
    assert bench["is_sample"] is False
    # Its governing corpus is also seeded (binding can validate).
    corpora = {c["id"] for c in client.get("/api/corpora").json()}
    assert "ainative-field-notes" in corpora


def test_full_loop_run_leaderboard_failure_and_receipts(client):
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good", "mock_bad"],
        "brief": {
            "task_name": "Memo summarization",
            "decision_question": "Which model to trust?",
            "success_criteria": "",
        },
    }
    report = client.post("/api/runs", json=body).json()

    # Leaderboard ranks mock_good first and marks it recommended.
    top = report["leaderboard"][0]
    assert top["candidate_id"] == "mock_good"
    assert top["recommended"] is True

    # At least one failure case exists to inspect.
    assert any(not r["passed"] for r in report["results"])

    run_id = report["run"]["id"]
    assert client.get(f"/api/runs/{run_id}").status_code == 200

    # All three receipt formats download with provenance.
    for fmt in ("json", "md", "html"):
        resp = client.get(f"/api/runs/{run_id}/receipt.{fmt}")
        assert resp.status_code == 200
        assert report["run"]["config_hash"] in resp.text
        assert "attachment" in resp.headers["content-disposition"]


def test_latest_run_is_null_before_any_run_then_returns_newest(client):
    # No runs yet → the at-rest rail hydrate endpoint returns null (honest "—"), not an error.
    empty = client.get("/api/runs/latest")
    assert empty.status_code == 200
    assert empty.json() is None

    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good", "mock_bad"],
        "brief": {
            "task_name": "Memo summarization",
            "decision_question": "Which model to trust?",
            "success_criteria": "",
        },
    }
    client.post("/api/runs", json=body)
    client.post("/api/runs", json=body)

    latest = client.get("/api/runs/latest")
    assert latest.status_code == 200
    # /runs/latest is the head of list_runs (newest-first, drafts dropped) — the rail's at-rest
    # receipt. Assert it agrees with /runs[0] rather than positing sub-second ordering the
    # whole-second created_at can't provide.
    listing = client.get("/api/runs").json()
    assert latest.json()["run"]["id"] == listing[0]["run"]["id"]


def test_gpu_idle_returns_null_and_never_shells_out_when_optin_is_off(client, monkeypatch):
    # The privileged powermetrics read MUST NOT fire without the operator's opt-in. Default is off.
    import orionfold.server.routes as routes

    called = {"powermetrics": False}

    def _spy_powermetrics():
        called["powermetrics"] = True
        return 42.0

    monkeypatch.setattr(routes, "_powermetrics_gpu_util", _spy_powermetrics)
    monkeypatch.setattr(routes, "_nvidia_gpu_util", lambda: None)

    resp = client.get("/api/telemetry/gpu-idle")
    assert resp.status_code == 200
    assert resp.json() == {"gpu_util": None}
    assert called["powermetrics"] is False  # no privileged shell-out without consent


def test_gpu_idle_reads_the_gpu_when_optin_is_on(client, monkeypatch):
    import orionfold.server.routes as routes

    # Turn the opt-in on, then a single read returns the parsed idle %.
    client.put("/api/settings", json={"powermetrics_gpu_optin": True})
    monkeypatch.setattr(routes, "_nvidia_gpu_util", lambda: None)
    monkeypatch.setattr(routes, "_powermetrics_gpu_util", lambda: 20.7)

    resp = client.get("/api/telemetry/gpu-idle")
    assert resp.status_code == 200
    assert resp.json() == {"gpu_util": 20.7}


def test_gpu_idle_prefers_nvidia_unprivileged_read_when_present(client, monkeypatch):
    import orionfold.server.routes as routes

    # NVIDIA's query is unprivileged → always tried first, even with the opt-in off.
    nvidia_calls = {"n": 0}

    def _nv():
        nvidia_calls["n"] += 1
        return 33.0

    monkeypatch.setattr(routes, "_nvidia_gpu_util", _nv)
    monkeypatch.setattr(routes, "_powermetrics_gpu_util", lambda: pytest.fail("must not shell out"))

    resp = client.get("/api/telemetry/gpu-idle")
    assert resp.json() == {"gpu_util": 33.0}
    assert nvidia_calls["n"] == 1


def test_html_receipt_can_be_served_inline_for_preview(client):
    run_id = client.post(
        "/api/runs",
        json={
            "dataset_id": "investment-memo-summarization",
            "candidate_ids": ["mock_good", "mock_bad"],
            "brief": {
                "task_name": "Memo summarization",
                "decision_question": "Which model to trust?",
                "success_criteria": "",
            },
        },
    ).json()["run"]["id"]

    inline = client.get(f"/api/runs/{run_id}/receipt.html?inline=1")
    assert inline.status_code == 200
    assert inline.headers["content-type"].startswith("text/html")
    assert "inline" in inline.headers["content-disposition"]
    assert "attachment" not in inline.headers["content-disposition"]

    # Default stays a download, and the inline body is byte-identical.
    download = client.get(f"/api/runs/{run_id}/receipt.html")
    assert "attachment" in download.headers["content-disposition"]
    assert inline.text == download.text
    # The sandbox headers guard the renderable format regardless of disposition — assert them on
    # the download path too, so a future refactor can't silently scope them to inline only.
    assert download.headers["content-security-policy"] == "sandbox"
    assert download.headers["x-content-type-options"] == "nosniff"


def test_inline_html_receipt_is_sandboxed(client):
    run_id = client.post(
        "/api/runs",
        json={
            "dataset_id": "investment-memo-summarization",
            "candidate_ids": ["mock_good", "mock_bad"],
            "brief": {
                "task_name": "Memo summarization",
                "decision_question": "Which model to trust?",
                "success_criteria": "",
            },
        },
    ).json()["run"]["id"]

    resp = client.get(f"/api/runs/{run_id}/receipt.html?inline=1")
    assert resp.status_code == 200
    # Even rendered directly (not only in the iframe sandbox), the document is a sandboxed
    # opaque origin with no script execution, and its type cannot be sniffed.
    assert resp.headers["content-security-policy"] == "sandbox"
    assert resp.headers["x-content-type-options"] == "nosniff"


def test_unknown_dataset_is_rejected(client):
    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": "nope",
            "candidate_ids": ["mock_good"],
            "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
        },
    )
    assert resp.status_code == 404


def _parse_sse(text: str) -> list[dict]:
    """Collect the JSON payload of every ``data:`` frame in an SSE response body."""
    return [
        json.loads(line[len("data:") :].strip())
        for line in text.splitlines()
        if line.startswith("data:")
    ]


def test_run_stream_emits_start_progress_and_report(client):
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good", "mock_bad"],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    resp = client.post("/api/runs/stream", json=body)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(resp.text)

    start = events[0]
    assert start["type"] == "start"
    assert start["total"] == start["n_examples"] * 2  # two candidates
    assert [c["id"] for c in start["candidates"]] == ["mock_good", "mock_bad"]

    progress = [e for e in events if e["type"] == "progress"]
    # `done` is a monotonic consumer-side counter (1..total) regardless of completion order.
    assert [e["done"] for e in progress] == list(range(1, start["total"] + 1))
    # Candidates run concurrently → cells can complete out of order, so assert the SET of cells
    # covers the full matrix (every candidate × every example) rather than a fixed order.
    n = start["n_examples"]
    expected_cells = {(cid, i) for cid in ("mock_good", "mock_bad") for i in range(n)}
    assert {(e["candidate_id"], e["example_index"]) for e in progress} == expected_cells

    report = events[-1]
    assert report["type"] == "report"
    assert report["report"]["leaderboard"][0]["candidate_id"] == "mock_good"

    # The streamed run was persisted just like a batch run.
    run_id = report["report"]["run"]["id"]
    assert client.get(f"/api/runs/{run_id}").status_code == 200


def test_run_stream_rejects_unknown_dataset(client):
    resp = client.post(
        "/api/runs/stream",
        json={
            "dataset_id": "nope",
            "candidate_ids": ["mock_good"],
            "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
        },
    )
    assert resp.status_code == 404


def test_preview_dataset_returns_pairs_without_writing(client):
    before = len(client.get("/api/datasets").json())
    resp = client.post(
        "/api/datasets/preview",
        json={"format": "jsonl", "text": '{"input":"a","expected":"b"}\nbad\n'},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["examples"][0]["input_text"] == "a"
    assert len(body["warnings"]) == 1
    # No write happened.
    assert len(client.get("/api/datasets").json()) == before


def test_preview_zero_valid_is_422(client):
    resp = client.post("/api/datasets/preview", json={"format": "jsonl", "text": "\n\n"})
    assert resp.status_code == 422


def test_create_dataset_round_trips_and_appears_in_list(client):
    resp = client.post(
        "/api/datasets",
        json={
            "name": "Client Summaries",
            "format": "csv",
            "text": "input,expected\nhello,world\n",
        },
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] == "client-summaries"
    # A plain (non-bench) example: the core tri-fields plus the defaulted bench/advisory contract
    # (additive in v9 — bench fields default to empty, so a non-bench import carries them inert).
    assert created["examples"] == [
        {
            "input_text": "hello",
            "expected_text": "world",
            "keypoints": [],
            "expected_behavior": None,
            "expected_citations": [],
            "accepted_source_ids": [],
            "requires_citation": False,
            "requires_refusal": False,
            "requires_route": False,
        }
    ]
    ids = {d["id"] for d in client.get("/api/datasets").json()}
    assert "client-summaries" in ids


def test_create_duplicate_name_is_409(client):
    body = {"name": "Dupe", "format": "jsonl", "text": '{"input":"a","expected":"b"}'}
    assert client.post("/api/datasets", json=body).status_code == 201
    assert client.post("/api/datasets", json=body).status_code == 409


def test_create_zero_valid_is_422(client):
    resp = client.post(
        "/api/datasets", json={"name": "Empty", "format": "jsonl", "text": "\n"}
    )
    assert resp.status_code == 422


def test_inline_receipt_theme_param_injects_data_theme(client):
    run_id = client.post(
        "/api/runs",
        json={
            "dataset_id": "investment-memo-summarization",
            "candidate_ids": ["mock_good", "mock_bad"],
            "brief": {"task_name": "Memo", "decision_question": "Which?", "success_criteria": ""},
        },
    ).json()["run"]["id"]

    light = client.get(f"/api/runs/{run_id}/receipt.html?inline=1&theme=light")
    assert light.status_code == 200
    assert 'data-theme="light"' in light.text.split("<head>")[0]

    # A plain download pins no theme (it self-adapts via prefers-color-scheme).
    download = client.get(f"/api/runs/{run_id}/receipt.html")
    assert "data-theme=" not in download.text.split("<head>")[0]


def test_inline_receipt_rejects_unknown_theme_without_reflecting_it(client):
    run_id = client.post(
        "/api/runs",
        json={
            "dataset_id": "investment-memo-summarization",
            "candidate_ids": ["mock_good", "mock_bad"],
            "brief": {"task_name": "Memo", "decision_question": "Which?", "success_criteria": ""},
        },
    ).json()["run"]["id"]

    payload = '"><script>alert(1)</script>'
    r = client.get(f"/api/runs/{run_id}/receipt.html", params={"inline": 1, "theme": payload})
    assert r.status_code == 200
    # An unknown theme is not pinned on <html>, and the payload is never reflected anywhere.
    assert "data-theme=" not in r.text.split("<head>")[0]
    assert "<script>alert(1)" not in r.text


def test_catalog_endpoint_returns_validated_catalog(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    body = resp.json()

    # Parses back into the schema (shape contract).
    catalog = ModelCatalog.model_validate(body)
    assert catalog.version >= 1

    providers = {p.id: p for p in catalog.providers}
    assert {"anthropic", "openai", "gemini", "openrouter", "ollama", "lmstudio"} <= providers.keys()
    # Privacy boundary is representable (cloud vs local) for the UI/recipes to label.
    assert providers["anthropic"].privacy == "cloud"
    assert providers["ollama"].privacy == "local"


def test_run_rejects_composite_id_for_unavailable_provider(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    datasets = client.get("/api/datasets").json()
    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": datasets[0]["id"],
            "candidate_ids": ["anthropic:claude-opus-4-8"],
            "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
        },
    )
    assert resp.status_code == 400
    assert "Unknown candidate(s)" in resp.json()["detail"]


def test_selection_endpoint_has_no_mocks_by_default(client, tmp_path, monkeypatch):
    # Mocks are off the happy path: with Sandbox off (default), /selection shows no mock group.
    monkeypatch.chdir(tmp_path)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    body = client.get("/api/selection").json()
    providers = body["providers"]
    assert all(p["provider_id"] not in ("mock", "mock_good", "mock_bad") for p in providers)
    groups = {p["provider_id"]: p for p in providers}
    assert groups["anthropic"]["available"] is False  # no key
    assert groups["ollama"]["available"] is True
    sample = groups["anthropic"]["models"][0]
    assert sample["candidate_id"] == f"anthropic:{sample['model']}"


def test_settings_default_and_update(client):
    # GET returns the full resolved settings: sandbox off + the built-in per-kind threshold map.
    initial = client.get("/api/settings").json()
    assert initial["sandbox_enabled"] is False
    assert initial["thresholds"] == {"similarity": 0.55, "keypoint": 0.8, "judge": 0.8}

    # PUT is partial — sending only sandbox leaves thresholds untouched.
    updated = client.put("/api/settings", json={"sandbox_enabled": True}).json()
    assert updated["sandbox_enabled"] is True
    assert updated["thresholds"] == initial["thresholds"]
    assert client.get("/api/settings").json()["sandbox_enabled"] is True


def test_settings_powermetrics_optin_round_trips(client):
    # Defaults off; PUT is partial so toggling it leaves sandbox + thresholds untouched.
    assert client.get("/api/settings").json()["powermetrics_gpu_optin"] is False
    updated = client.put("/api/settings", json={"powermetrics_gpu_optin": True}).json()
    assert updated["powermetrics_gpu_optin"] is True
    assert updated["sandbox_enabled"] is False
    assert client.get("/api/settings").json()["powermetrics_gpu_optin"] is True


def test_settings_threshold_override_round_trips(client):
    # PUT only thresholds → persisted and reflected; sandbox stays untouched.
    resp = client.put(
        "/api/settings",
        json={"thresholds": {"similarity": 0.7, "keypoint": 0.8, "judge": 0.9}},
    ).json()
    assert resp["thresholds"] == {"similarity": 0.7, "keypoint": 0.8, "judge": 0.9}
    assert resp["sandbox_enabled"] is False
    assert client.get("/api/settings").json()["thresholds"]["similarity"] == 0.7


def test_settings_threshold_override_drives_auto_default(client):
    # After lowering the similarity default, an Auto similarity run prefills the override threshold.
    client.put(
        "/api/settings",
        json={"thresholds": {"similarity": 0.3, "keypoint": 0.8, "judge": 0.8}},
    )
    # A label-style dataset (no keypoints) so Auto resolves to similarity.
    ds = client.post(
        "/api/datasets",
        json={"name": "labels", "format": "csv", "text": "input,expected\ni,billing\n"},
    ).json()
    report = client.post(
        "/api/runs",
        json={
            "dataset_id": ds["id"],
            "candidate_ids": ["mock_good"],
            "brief": {"task_name": "t", "decision_question": "q"},
        },
    ).json()
    assert report["run"]["rubric"]["kind"] == "similarity"
    assert report["run"]["rubric"]["threshold"] == 0.3


def test_selection_is_sandbox_aware(client):
    assert all(
        g["provider_id"] != "mock" for g in client.get("/api/selection").json()["providers"]
    )
    client.put("/api/settings", json={"sandbox_enabled": True})
    mock = [
        g for g in client.get("/api/selection").json()["providers"] if g["provider_id"] == "mock"
    ]
    assert len(mock) == 1 and len(mock[0]["models"]) == 2


def test_seed_then_remove_sample_data(client):
    from orionfold import sample_data

    n = len(sample_data._SAMPLES)
    assert client.post("/api/sample-data/seed").json() == {"datasets": n, "receipts": n}
    ds = client.get("/api/datasets").json()
    assert any(d["is_sample"] for d in ds)
    assert len(client.get("/api/runs").json()) == n
    assert client.request("DELETE", "/api/sample-data").json() == {"datasets": n, "receipts": n}
    assert not any(d["is_sample"] for d in client.get("/api/datasets").json())
    assert client.get("/api/runs").json() == []


def test_clear_all_data(client):
    from orionfold import sample_data

    client.post("/api/sample-data/seed")
    out = client.request("DELETE", "/api/data").json()
    assert out["receipts"] == len(sample_data._SAMPLES) and out["datasets"] >= 1
    assert client.get("/api/datasets").json() == []


def test_selection_endpoint_leaks_no_secrets(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-appear")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-never-appear")
    text = client.get("/api/selection").text
    assert "sk-ant-should-never-appear" not in text
    assert "sk-should-never-appear" not in text
    assert "API_KEY" not in text


def test_catalog_endpoint_leaks_no_secrets(client, monkeypatch):
    # Even with keys present in the environment, the catalog body must contain no credential-ish
    # strings — it is static reference data with no key fields.
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-never-appear-in-catalog")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-appear")
    text = client.get("/api/catalog").text
    assert "sk-should-never-appear-in-catalog" not in text
    assert "sk-ant-should-never-appear" not in text
    assert "API_KEY" not in text


# ---------------------------------------------------------------------------
# Task 7: optional rubric (Auto default), judge 422, cost_summary in report
# ---------------------------------------------------------------------------

_DEMO_DATASET_ID = "investment-memo-summarization"


def test_run_omitting_rubric_uses_keypoint_default(client):
    # The seeded demo dataset carries keypoints, so Auto resolves to keypoint.
    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": _DEMO_DATASET_ID,
            "candidate_ids": ["mock_good"],
            "brief": {"task_name": "t", "decision_question": "q"},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["run"]["rubric"]["kind"] == "keypoint"


def test_run_judge_without_model_is_422(client):
    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": _DEMO_DATASET_ID,
            "candidate_ids": ["mock_good"],
            "rubric": {"kind": "judge", "threshold": 0.8, "case_sensitive": False},
            "brief": {"task_name": "t", "decision_question": "q"},
        },
    )
    assert resp.status_code == 422


def test_run_report_has_cost_summary(client):
    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": _DEMO_DATASET_ID,
            "candidate_ids": ["mock_good"],
            "rubric": {"kind": "keypoint", "threshold": 0.8, "case_sensitive": False},
            "brief": {"task_name": "t", "decision_question": "q"},
        },
    )
    assert resp.status_code == 200
    assert "cost_summary" in resp.json()


def test_run_judge_with_unavailable_provider_is_422(client, tmp_path, monkeypatch):
    """Regression: unavailable but well-formed judge_provider_id must return 422, not 500."""
    # Ensure openai is NOT available (no key set).
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", str(tmp_path / "absent.env"))
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    resp = client.post(
        "/api/runs",
        json={
            "dataset_id": _DEMO_DATASET_ID,
            "candidate_ids": ["mock_good"],
            "rubric": {
                "kind": "judge",
                "threshold": 0.8,
                "case_sensitive": False,
                "judge_provider_id": "openai",
                "judge_model": "x",
            },
            "brief": {"task_name": "t", "decision_question": "q"},
        },
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Task 4: RunRequest.prompt_variants — fan one model into N prompts
# ---------------------------------------------------------------------------


def test_prompt_variant_run_produces_one_entry_per_variant(client):
    body = {
        "dataset_id": "investment-memo-summarization",
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


def test_prompt_variant_run_scores_differ_baseline_beats_concise(client):
    # Keyless signal: a concise prompt drops keypoints, so it scores below a full-output prompt.
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good"],
        "prompt_variants": [
            {"name": "Baseline", "system_prompt": "Complete the task. Output only the result."},
            {"name": "Concise", "system_prompt": "Answer in as few words as possible."},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    r = client.post("/api/runs", json=body)
    assert r.status_code == 200, r.text
    by_label = {e["label"]: e for e in r.json()["leaderboard"]}
    assert by_label["Baseline"]["avg_score"] > by_label["Concise"]["avg_score"]


def test_prompt_variant_run_rejects_multiple_models(client):
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good", "mock_bad"],
        "prompt_variants": [
            {"name": "A", "system_prompt": "x"},
            {"name": "B", "system_prompt": "y"},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    assert client.post("/api/runs", json=body).status_code == 422


def test_prompt_variant_run_rejects_fewer_than_two(client):
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good"],
        "prompt_variants": [{"name": "Only", "system_prompt": "x"}],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    assert client.post("/api/runs", json=body).status_code == 422


def test_prompt_variant_run_rejects_empty_fields(client):
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good"],
        "prompt_variants": [
            {"name": "A", "system_prompt": "  "},
            {"name": "  ", "system_prompt": "y"},
        ],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    assert client.post("/api/runs", json=body).status_code == 422


def test_create_with_tags_and_check_hint_round_trips(client):
    body = {
        "name": "Tagged via API",
        "format": "jsonl",
        "text": '{"input": "x", "expected": "y"}',
        "tags": ["Legal", "Finance"],
        "check_hint": "substring",
    }
    assert client.post("/api/datasets", json=body).status_code == 201
    rows = {d["name"]: d for d in client.get("/api/datasets").json()}
    row = rows["Tagged via API"]
    assert row["tags"] == ["Legal", "Finance"]
    assert row["check_hint"] == "substring"
    assert row["created_at"]  # stamped, non-empty
    assert row["source"] == "pasted"


def test_patch_dataset_updates_tags_and_404s_for_unknown(client):
    client.post(
        "/api/datasets",
        json={"name": "Patchable", "format": "jsonl", "text": '{"input": "a", "expected": "b"}'},
    )
    ds_id = {d["name"]: d for d in client.get("/api/datasets").json()}["Patchable"]["id"]
    res = client.patch(f"/api/datasets/{ds_id}", json={"tags": ["Support"], "check_hint": "exact"})
    assert res.status_code == 200
    assert res.json()["tags"] == ["Support"]
    assert res.json()["check_hint"] == "exact"
    assert client.patch("/api/datasets/does-not-exist", json={"tags": ["x"]}).status_code == 404


def _xlsx_upload_bytes() -> bytes:
    import io as _io

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["input", "expected"])
    ws.append(["Ping?", "Pong."])
    buf = _io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_extract_xlsx_returns_csv_text_without_writing(client):
    before = len(client.get("/api/datasets").json())
    files = {
        "file": (
            "cases.xlsx",
            _xlsx_upload_bytes(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    res = client.post("/api/datasets/extract", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == "csv"
    assert "Ping?" in body["text"]
    assert len(client.get("/api/datasets").json()) == before  # no write


def test_extract_rejects_unknown_extension(client):
    files = {"file": ("notes.txt", b"hello", "text/plain")}
    assert client.post("/api/datasets/extract", files=files).status_code == 422


# ─── Quick-compare (inline examples, human pick) ──────────────────────────────


def test_quick_run_uses_inline_examples_without_a_dataset_row(client):
    body = {
        "examples": [{"input_text": "Summarize: revenue grew 22%.", "expected_text": ""}],
        "candidate_ids": ["mock_good", "mock_bad"],
        "rubric": {"kind": "none", "threshold": 0, "case_sensitive": False},
        "mode": "quick",
        "brief": {"task_name": "Quick check", "decision_question": "Which reads better?"},
    }
    res = client.post("/api/runs", json=body)
    assert res.status_code == 200, res.text
    report = res.json()
    assert report["run"]["mode"] == "quick"
    assert report["run"]["dataset_id"] == "quick-compare"
    assert report["run"]["chosen_winner"] is None
    assert len(report["results"]) == 2
    assert all(r["score"] is None for r in report["results"])
    # No dataset row was created for the ad-hoc prompt.
    ds = client.get("/api/datasets").json()
    assert all(d["id"] != "quick-compare" for d in ds)


def _make_quick_run(client) -> str:
    body = {
        "examples": [{"input_text": "x", "expected_text": ""}],
        "candidate_ids": ["mock_good", "mock_bad"],
        "rubric": {"kind": "none", "threshold": 0, "case_sensitive": False},
        "mode": "quick",
        "brief": {"task_name": "Quick check", "decision_question": "q"},
    }
    return client.post("/api/runs", json=body).json()["run"]["id"]


def test_patch_winner_records_pick_and_keeps_config_hash(client):
    run_id = _make_quick_run(client)
    before = client.get(f"/api/runs/{run_id}").json()
    res = client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "mock_good"})
    assert res.status_code == 200, res.text
    after = res.json()
    assert after["run"]["chosen_winner"] == "mock_good"
    assert after["run"]["config_hash"] == before["run"]["config_hash"]  # invariant
    # "tie" is a legitimate pick.
    tie = client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "tie"})
    assert tie.status_code == 200


def test_patch_winner_rejects_unknown_candidate(client):
    run_id = _make_quick_run(client)
    res = client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "nope"})
    assert res.status_code == 400


def test_patch_winner_404_for_unknown_run(client):
    res = client.patch("/api/runs/run_missing/winner", json={"chosen_winner": "tie"})
    assert res.status_code == 404


def test_unpicked_quick_runs_are_hidden_from_the_list(client):
    run_id = _make_quick_run(client)
    listed = client.get("/api/runs").json()
    assert all(r["run"]["id"] != run_id for r in listed)  # no pick yet → hidden
    client.patch(f"/api/runs/{run_id}/winner", json={"chosen_winner": "tie"})
    listed = client.get("/api/runs").json()
    assert any(r["run"]["id"] == run_id for r in listed)   # picked → visible


def _make_full_run(client, dataset_id: str = "investment-memo-summarization") -> dict:
    body = {
        "dataset_id": dataset_id,
        "candidate_ids": ["mock_good", "mock_bad"],
        "brief": {
            "task_name": "Memo summarization",
            "decision_question": "Which model to trust?",
            "success_criteria": "",
        },
    }
    res = client.post("/api/runs", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_track_record_pools_runs_over_the_same_comparable_slice(client):
    # Two scored runs over the same (dataset, rubric kind) roll up into one group with a pooled
    # pass-rate (Σpasses / Σexamples), not a mean of the two runs' rates.
    r1 = _make_full_run(client)
    r2 = _make_full_run(client)
    kind = r1["run"]["rubric"]["kind"]
    assert kind != "none"  # the sample resolves to a scored rubric

    groups = client.get("/api/track-record").json()
    assert len(groups) == 1
    group = groups[0]
    assert group["dataset_id"] == "investment-memo-summarization"
    assert group["rubric_kind"] == kind
    assert group["runs"] == 2

    # mock_good ranks first; its pooled pass-rate equals total_passes / total_examples and its
    # run-count reflects both runs.
    top = group["entries"][0]
    assert top["candidate_id"] == "mock_good"
    assert top["runs"] == 2
    # Pooled over both runs: each scored the 5-example sample, so Σexamples = 5 × 2.
    per_run_examples = len(r1["results"]) // len(r1["leaderboard"])
    assert top["total_examples"] == per_run_examples * 2
    assert top["pass_rate"] == pytest.approx(top["total_passes"] / top["total_examples"])
    # times_recommended counts the runs that crowned this candidate (both, for mock_good).
    lb1_winner = next(e for e in r1["leaderboard"] if e["recommended"])
    lb2_winner = next(e for e in r2["leaderboard"] if e["recommended"])
    expected_wins = sum(w["candidate_id"] == "mock_good" for w in (lb1_winner, lb2_winner))
    assert top["times_recommended"] == expected_wins


def test_track_record_filter_and_quick_exclusion(client):
    _make_full_run(client)
    # A quick run is unscored (rubric kind "none") — invisible to the rollup.
    _make_quick_run(client)
    groups = client.get("/api/track-record").json()
    assert all(g["rubric_kind"] != "none" for g in groups)
    assert {g["dataset_id"] for g in groups} == {"investment-memo-summarization"}

    # ?dataset_id narrows to that dataset; an unknown id yields no groups.
    narrowed = client.get(
        "/api/track-record", params={"dataset_id": "investment-memo-summarization"}
    ).json()
    assert len(narrowed) == 1
    assert client.get("/api/track-record", params={"dataset_id": "nope"}).json() == []


def test_cost_summary_rolls_stored_runs_into_an_eval_judge_split(client):
    # No stored runs yet → an honest zero rollup, not an error.
    empty = client.get("/api/cost-summary", params={"window": "all"}).json()
    assert empty["run_count"] == 0
    assert empty["total_cost_usd"] == 0.0
    assert empty["trend"] == []

    # Two scored runs (both created "now") roll up. Mocks are free, so the split is 0/0 — what we
    # assert is the structure and that both runs are counted with an oldest-first trend.
    r1 = _make_full_run(client)
    r2 = _make_full_run(client)

    today = client.get("/api/cost-summary", params={"window": "today"}).json()
    assert today["window"] == "today"
    assert today["run_count"] == 2  # both created today
    # total == eval + judge always holds.
    assert today["total_cost_usd"] == pytest.approx(
        today["eval_cost_usd"] + today["judge_cost_usd"]
    )
    # Trend carries one point per run, oldest-first, each with a pooled pass-rate.
    trend_ids = [p["run_id"] for p in today["trend"]]
    assert set(trend_ids) == {r1["run"]["id"], r2["run"]["id"]}
    assert today["trend"] == sorted(today["trend"], key=lambda p: (p["created_at"], p["run_id"]))
    assert all(0.0 <= p["pass_rate"] <= 1.0 for p in today["trend"])

    # window=all is cumulative; with only today's runs it matches the today rollup's run_count.
    all_window = client.get("/api/cost-summary", params={"window": "all"}).json()
    assert all_window["window"] == "all"
    assert all_window["run_count"] == 2


def test_cost_summary_excludes_unpicked_quick_drafts(client):
    # A quick-compare draft with no pick is not a receipt — its spend must not inflate the rail.
    _make_full_run(client)
    _make_quick_run(client)  # no winner recorded
    roll = client.get("/api/cost-summary", params={"window": "all"}).json()
    assert roll["run_count"] == 1  # only the full run counts


# ─── v9: Corpus route + bench-run binding validation ──────────────────────────────────


def test_corpora_route_lists_bundled_corpus(client):
    corpora = client.get("/api/corpora").json()
    ids = {c["id"] for c in corpora}
    assert "ainative-field-notes" in ids
    fn = next(c for c in corpora if c["id"] == "ainative-field-notes")
    assert len(fn["source_ids"]) > 0


def test_bench_run_against_unbound_dataset_is_400(client):
    # A non-bench dataset has no corpus_id; forcing a bench rubric must fail the binding gate.
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good"],
        "rubric": {"kind": "bench"},
        "brief": {"task_name": "t", "decision_question": "q?"},
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 400
    assert "corpus" in resp.json()["detail"].lower()


def test_bench_run_on_bound_dataset_produces_governance_receipt(client, tmp_path):
    # Create a corpus + a bench dataset bound to it via the repository, then run it through the API
    # and confirm the receipt is scored by the governance bench (not similarity/keypoint).
    from orionfold.domain.models import Corpus, Example
    from orionfold.storage.db import connect
    from orionfold.storage.repository import save_dataset, upsert_corpus

    conn = connect(tmp_path / "proof.db")
    upsert_corpus(conn, Corpus(id="fn-test", name="FN", source_ids=["doc_guide"]))
    ds = save_dataset(
        conn, "Bench API set", "d",
        [Example(input_text="How is the storefront positioned?",
                 expected_text="The guide governs it.\nCitations: [doc_guide]",
                 expected_behavior="answer", expected_citations=["doc_guide"])],
        corpus_id="fn-test",
    )
    conn.close()

    body = {
        "dataset_id": ds.id,
        "candidate_ids": ["mock_good"],
        "rubric": {"kind": "bench"},
        "brief": {"task_name": "Governance", "decision_question": "Cites right?"},
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == 200
    report = resp.json()
    assert report["run"]["rubric"]["kind"] == "bench"
    # The receipt's scored-by descriptor is the governance bench (deterministic, no threshold).
    from orionfold.domain.models import ProofReport
    from orionfold.receipts import export

    scored_by = export.build_receipt(ProofReport.model_validate(report))["scored_by"]
    assert scored_by.startswith("Governance bench")


def test_corpus_sources_enriches_from_bound_bench_examples(client):
    # The bundled Advisor bench binds the ainative-field-notes corpus and flattens its sources into
    # each example's input_text. The derived endpoint parses them into enriched, cross-linked records.
    resp = client.get("/api/corpora/ainative-field-notes/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) > 0
    by_id = {s["id"]: s for s in sources}
    # A known cited source from example 0 — enriched with a real title/class and a citation count.
    cited = by_id["article_hermes_serving_lane_on_spark"]
    assert cited["title"]  # non-empty derived title
    assert cited["class"]  # serialized under the alias, not "klass"
    assert cited["cited_by"] >= 1


def test_corpus_sources_unknown_id_is_404(client):
    assert client.get("/api/corpora/no-such-corpus/sources").status_code == 404


def test_telemetry_host_returns_profile(client):
    r = client.get("/api/telemetry/host")
    assert r.status_code == 200
    body = r.json()
    assert "arch" in body and body["arch"]
    # local_runtime is present (may be None when no real local server is reachable). It must
    # NEVER report a mock provider — mocks carry privacy="local" to simulate a local model for
    # the keyless demo, but they are not a hardware runtime and would mislead the Host panel.
    assert "local_runtime" in body
    assert body["local_runtime"] not in ("mock_good", "mock_bad")


def test_run_report_carries_host_context(client):
    body = {
        "dataset_id": "investment-memo-summarization",
        "candidate_ids": ["mock_good"],
        "brief": {"task_name": "t", "decision_question": "q", "success_criteria": ""},
    }
    report = client.post("/api/runs", json=body).json()
    # A real run (CLI/route path) attaches the static host profile; presentation-only.
    assert report["host"] is not None
    assert report["host"]["arch"]
    # The non-stream endpoint does no live sampling → telemetry stays None (honest absence).
    assert report.get("telemetry") is None
