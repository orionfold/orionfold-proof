# tests/integration/test_recipes_api.py
"""The recipes panel + inline credential endpoint. Keys stay in a tmp .env.local and are never
echoed back."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orionfold.server.app import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Confine .env.local to tmp and clear ambient keys so the panel is hermetic.
    monkeypatch.setenv("ORIONFOLD_ENV_FILE", str(tmp_path / ".env.local"))
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    app = create_app(db_path=tmp_path / "proof.db")
    with TestClient(app) as c:  # triggers lifespan: migrate + seed
        yield c


def test_recipes_panel_shape(client):
    body = client.get("/api/recipes").json()
    ids = [r["id"] for r in body["recipes"]]
    assert "cost-vs-quality" in ids
    cvq = next(r for r in body["recipes"] if r["id"] == "cost-vs-quality")
    assert cvq["candidate_ids"] == []  # keyless => fully unmet
    assert cvq["unmet"][0]["key_name"] == "ANTHROPIC_API_KEY"


def test_credentials_writes_and_flips_availability(client):
    before = client.get("/api/recipes").json()
    cvq_before = next(r for r in before["recipes"] if r["id"] == "cost-vs-quality")
    assert cvq_before["candidate_ids"] == []

    res = client.post("/api/credentials", json={"provider_id": "anthropic", "key": "sk-ant-xyz"})
    assert res.status_code == 200
    data = res.json()
    assert data == {"provider_id": "anthropic", "available": True}
    assert "sk-ant-xyz" not in res.text  # never echoed

    after = client.get("/api/recipes").json()
    cvq_after = next(r for r in after["recipes"] if r["id"] == "cost-vs-quality")
    assert len(cvq_after["candidate_ids"]) == 2  # now resolves


def test_credentials_rejects_unknown_provider(client):
    assert client.post("/api/credentials", json={"provider_id": "ollama", "key": "x"}).status_code == 400
    assert client.post("/api/credentials", json={"provider_id": "mock_good", "key": "x"}).status_code == 400


def test_credentials_rejects_empty_key(client):
    assert client.post("/api/credentials", json={"provider_id": "anthropic", "key": "  "}).status_code == 422
