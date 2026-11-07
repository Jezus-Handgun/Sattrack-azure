import base64
import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def principal(claims):
    return base64.b64encode(json.dumps({"auth_typ": "aad", "claims": claims}).encode()).decode()


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


def test_me_local_mode_without_headers():
    response = client.get("/api/me")
    assert response.status_code == 200
    assert response.json() == {"name": None, "login": None, "mode": "local"}


def test_me_with_principal_name_header():
    response = client.get("/api/me", headers={"X-MS-CLIENT-PRINCIPAL-NAME": "jan@firma.pl"})
    assert response.json() == {"name": "jan@firma.pl", "login": "jan@firma.pl", "mode": "azure"}


def test_me_prefers_name_claim():
    headers = {
        "X-MS-CLIENT-PRINCIPAL-NAME": "jan@firma.pl",
        "X-MS-CLIENT-PRINCIPAL": principal(
            [
                {"typ": "preferred_username", "val": "jan@firma.pl"},
                {"typ": "name", "val": "Jan Nowak"},
            ]
        ),
    }
    assert client.get("/api/me", headers=headers).json()["name"] == "Jan Nowak"


def test_me_malformed_principal_falls_back_to_login():
    headers = {"X-MS-CLIENT-PRINCIPAL-NAME": "jan@firma.pl", "X-MS-CLIENT-PRINCIPAL": "%%%"}
    assert client.get("/api/me", headers=headers).json()["name"] == "jan@firma.pl"
