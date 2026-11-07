import httpx
import pytest

from app.tle_store import GROUPS, SNAPSHOT_DIR, TleStore

GPS_TEXT = (SNAPSHOT_DIR / "gps.tle").read_text()


def make_store(tmp_path, handler, ttl=7200):
    calls = []

    def counting(request):
        calls.append(request)
        return handler(request)

    client = httpx.Client(transport=httpx.MockTransport(counting))
    store = TleStore(tmp_path / "tle", ttl, client=client)
    store.load_initial()
    return store, calls


def ok(request):
    return httpx.Response(200, text=GPS_TEXT)


def forbidden(request):
    return httpx.Response(403, text="GP data has not updated since your last successful download")


def timeout(request):
    raise httpx.ReadTimeout("timed out", request=request)


def test_initial_load_uses_snapshot_without_network(tmp_path):
    store, calls = make_store(tmp_path, ok)
    for key in GROUPS:
        assert store._data[key].source == "snapshot"
        assert store._data[key].satellites
    assert calls == []


def test_first_get_fetches_and_writes_cache(tmp_path):
    store, calls = make_store(tmp_path, ok)
    data = store.get("gps")
    assert data.source == "live"
    assert data.fetched_at is not None
    assert len(calls) == 1
    assert calls[0].url.params["GROUP"] == "gps-ops"
    assert "SatTrack" in calls[0].headers["User-Agent"]
    assert (tmp_path / "tle" / "gps.tle").exists()


def test_no_refetch_within_ttl(tmp_path):
    store, calls = make_store(tmp_path, ok)
    store.get("gps")
    store.get("gps")
    assert len(calls) == 1


def test_refetch_after_ttl(tmp_path):
    store, calls = make_store(tmp_path, ok, ttl=0)
    store.get("gps")
    store.get("gps")
    assert len(calls) == 2


@pytest.mark.parametrize("handler", [forbidden, timeout])
def test_error_falls_back_to_snapshot_without_retry(tmp_path, handler):
    store, calls = make_store(tmp_path, handler)
    for _ in range(3):
        data = store.get("gps")
        assert data.source == "snapshot"
        assert data.satellites
    assert len(calls) == 1  # one attempt, then wait for the TTL even after a failure


def test_empty_response_does_not_overwrite_good_data(tmp_path):
    store, _ = make_store(tmp_path, lambda r: httpx.Response(200, text="No GP data found"))
    assert store.get("gps").source == "snapshot"
    assert not (tmp_path / "tle" / "gps.tle").exists()


def test_restart_uses_cache_file_and_skips_fetch(tmp_path):
    first, _ = make_store(tmp_path, ok)
    first.get("gps")

    second, calls = make_store(tmp_path, ok)
    assert second.get("gps").source == "cache"
    assert calls == []


def test_find_by_norad_id(tmp_path):
    store, _ = make_store(tmp_path, ok)
    key, sat = store.find(25544)  # ISS
    assert key == "stations"
    assert "ISS" in sat.name
    assert store.find(1) is None
