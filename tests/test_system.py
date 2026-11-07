from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_served_at_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "SatTrack" in response.text
    assert client.get("/app.js").status_code == 200


def test_openapi_docs_enabled():
    assert client.get("/docs").status_code == 200
