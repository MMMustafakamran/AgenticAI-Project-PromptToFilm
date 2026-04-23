from fastapi.testclient import TestClient

from backend.app import app


def test_healthcheck():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
