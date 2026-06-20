"""End-to-end API loop over a temp DB — runs fully keyless (no providers, no network)."""

import pytest
from fastapi.testclient import TestClient

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
