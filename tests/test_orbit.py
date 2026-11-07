from datetime import UTC, datetime, timedelta

import pytest

from app import orbit

CHORZOW = (50.30, 18.95)
WHEN = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)  # close to the snapshot epoch


@pytest.fixture
def gnss(offline_store):
    return {key: offline_store.get(key).satellites for key in orbit.GNSS_GROUPS}


@pytest.fixture
def iss(offline_store):
    return offline_store.find(25544)[1]


def test_position_of_iss_is_realistic(iss):
    p = orbit.position(iss, WHEN)
    assert -52 <= p["lat"] <= 52  # inclination 51.6°
    assert 380 <= p["alt_km"] <= 450
    assert 7.5 <= p["speed_km_s"] <= 7.8


def test_ground_track_covers_90_minutes(iss):
    track = orbit.ground_track(iss, WHEN)
    assert len(track) == 91
    assert track[0]["time"] == WHEN - timedelta(minutes=45)
    assert track[-1]["time"] == WHEN + timedelta(minutes=45)


def test_visible_elevation_and_azimuth_ranges(gnss):
    sats = orbit.visible(gnss, *CHORZOW, WHEN, 10)
    assert sats
    for s in sats:
        assert 10 <= s["elevation_deg"] <= 90
        assert 0 <= s["azimuth_deg"] <= 360
    assert {s["constellation"] for s in sats} == set(orbit.GNSS_GROUPS)


def test_gps_visible_count_is_realistic_over_24h(gnss):
    _, counts = orbit.visibility_timeline(gnss, *CHORZOW, WHEN, 24, 10, 10)
    assert 4 <= min(counts["gps"]) and max(counts["gps"]) <= 14


def test_timeline_total_is_sum_and_aligned(gnss):
    times, counts = orbit.visibility_timeline(gnss, *CHORZOW, WHEN, 24, 10, 10)
    assert len(times) == 145
    for i in range(len(times)):
        assert counts["total"][i] == sum(counts[c][i] for c in orbit.GNSS_GROUPS)


def test_iss_passes_are_ordered(iss):
    passes = orbit.passes(iss, *CHORZOW, WHEN, 48, 10)
    assert passes
    for p in passes:
        assert p["rise"] < p["culmination"] < p["set"]
        assert 10 <= p["max_elevation_deg"] <= 90
    starts = [p["rise"] for p in passes]
    assert starts == sorted(starts)
