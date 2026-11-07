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
