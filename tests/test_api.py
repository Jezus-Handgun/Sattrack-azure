import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_groups_lists_all_groups_from_snapshot():
    response = client.get("/api/groups")
    assert response.status_code == 200
    groups = {g["key"]: g for g in response.json()}
    assert set(groups) == {"gps", "galileo", "glonass", "beidou", "stations"}
    for g in groups.values():
        assert g["count"] > 0
        assert g["source"] == "snapshot"
        assert g["fetched_at"] is None
        assert g["newest_epoch"] is not None


def test_satellites_in_group():
    response = client.get("/api/satellites", params={"group": "galileo"})
    assert response.status_code == 200
    sats = response.json()
    assert len(sats) > 20
    assert all(s["group"] == "galileo" for s in sats)


def test_satellite_detail_with_track():
    response = client.get("/api/satellites/25544")
    assert response.status_code == 200
    body = response.json()
    assert "ISS" in body["name"]
    assert len(body["track"]) == 91


def test_visible_at_given_time():
    params = {"lat": 50.3, "lon": 18.95, "time": "2026-11-07T12:00:00Z"}
    response = client.get("/api/visible", params=params)
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["total"] == len(body["satellites"]) > 0


def test_visibility_timeline():
    response = client.get("/api/visibility-timeline", params={"hours": 6, "step_min": 30})
    assert response.status_code == 200
    body = response.json()
    assert len(body["times"]) == 13
    assert set(body["counts"]) == {"gps", "galileo", "glonass", "beidou", "total"}


def test_iss_passes():
    response = client.get("/api/passes/25544", params={"lat": 50.3, "lon": 18.95})
    assert response.status_code == 200
    assert response.json()["passes"]


@pytest.mark.parametrize(
    "url",
    [
        "/api/visible?lat=91&lon=0",
        "/api/visible?lat=0&lon=-181",
        "/api/visibility-timeline?lat=-100",
        "/api/passes/25544?lon=200",
        "/api/satellites?group=starlink",
    ],
)
def test_invalid_params_return_422(url):
    assert client.get(url).status_code == 422


@pytest.mark.parametrize("url", ["/api/satellites/1", "/api/passes/1"])
def test_unknown_satellite_returns_404(url):
    assert client.get(url).status_code == 404
