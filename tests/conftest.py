import httpx
import pytest

from app.tle_store import store


def _no_network(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"test tried to reach the network: {request.url}")


@pytest.fixture(autouse=True)
def offline_store(tmp_path):
    """App-wide store runs on the snapshot only: empty cache dir, network calls fail the test."""
    store.cache_dir = tmp_path / "tle"
    store.client = httpx.Client(transport=httpx.MockTransport(_no_network))
    store.ttl = 10**9
    store._data.clear()
    store.load_initial()
    for key in store._data:
        store._last_attempt[key] = float("inf")  # never due for refresh
    yield store
