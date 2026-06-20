"""The local engine exposes a health endpoint under /api."""

from fastapi.testclient import TestClient

from orionfold import __version__
from orionfold.server.app import create_app


def test_health_endpoint_reports_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "orionfold-proof"
    assert body["version"] == __version__


def test_root_serves_a_response_without_a_built_cockpit() -> None:
    # On a fresh checkout the cockpit is not embedded; "/" must still respond
    # (placeholder) so `orionfold up` is never dead.
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Orionfold Proof" in response.text
