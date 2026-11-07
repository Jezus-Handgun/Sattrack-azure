"""Orbit computations with Skyfield (SGP4): positions, ground tracks, visibility, passes."""

from datetime import UTC, datetime, timedelta

import numpy as np
from skyfield.api import EarthSatellite, wgs84

from app.tle_store import ts

GNSS_GROUPS = ("gps", "galileo", "glonass", "beidou")


def _utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt  # naive input is treated as UTC


def to_time(dt: datetime):
    return ts.from_datetime(_utc(dt))


def time_range(start: datetime, minutes: range):
    # Built from exact datetimes so returned timestamps land on whole minutes (no float drift).
    start = _utc(start)
    return ts.from_datetimes([start + timedelta(minutes=m) for m in minutes])


def position(sat: EarthSatellite, dt: datetime) -> dict | None:
    """Sub-satellite point; None when SGP4 fails (e.g. decayed object with stale TLE)."""
    geo = sat.at(to_time(dt))
    lat, lon = wgs84.latlon_of(geo)
    if np.isnan(lat.degrees):
        return None
    return {
        "norad_id": sat.model.satnum,
        "name": sat.name,
        "lat": round(float(lat.degrees), 4),
        "lon": round(float(lon.degrees), 4),
        "alt_km": round(float(wgs84.height_of(geo).km), 1),
        "speed_km_s": round(float(np.linalg.norm(geo.velocity.km_per_s)), 3),
    }


def ground_track(sat: EarthSatellite, dt: datetime, minutes: int = 45) -> list[dict]:
    """Sub-satellite points every minute from -minutes to +minutes around dt."""
    times = time_range(dt, range(-minutes, minutes + 1))
    lat, lon = wgs84.latlon_of(sat.at(times))
    return [
        {"time": when, "lat": round(float(la), 4), "lon": round(float(lo), 4)}
        for when, la, lo in zip(times.utc_datetime(), lat.degrees, lon.degrees, strict=True)
        if not np.isnan(la)
    ]


def visible(
    groups: dict[str, list[EarthSatellite]], lat: float, lon: float, dt: datetime, min_el: float
) -> list[dict]:
    """Satellites above the elevation mask at one moment, highest first."""
    site = wgs84.latlon(lat, lon)
    t = to_time(dt)
    result = []
    for constellation, sats in groups.items():
        for sat in sats:
            alt, az, _ = (sat - site).at(t).altaz()
            if alt.degrees >= min_el:  # NaN (SGP4 error) compares False
                result.append(
                    {
                        "norad_id": sat.model.satnum,
                        "name": sat.name,
                        "constellation": constellation,
                        "elevation_deg": round(float(alt.degrees), 2),
                        "azimuth_deg": round(float(az.degrees), 2),
                    }
                )
    return sorted(result, key=lambda s: -s["elevation_deg"])


def visibility_timeline(
    groups: dict[str, list[EarthSatellite]],
    lat: float,
    lon: float,
    start: datetime,
    hours: int,
    step_min: int,
    min_el: float,
) -> tuple[list[datetime], dict[str, list[int]]]:
    """Number of visible satellites per constellation (and total) at each time step."""
    site = wgs84.latlon(lat, lon)
    times = time_range(start, range(0, hours * 60 + 1, step_min))
    counts = {}
    for constellation, sats in groups.items():
        above = np.zeros(len(times), dtype=int)
        for sat in sats:  # vectorised over time: one SGP4 call per satellite
            alt, _, _ = (sat - site).at(times).altaz()
            above += alt.degrees >= min_el
        counts[constellation] = above.tolist()
    counts["total"] = np.sum([counts[c] for c in groups], axis=0).tolist()
    return list(times.utc_datetime()), counts


def passes(
    sat: EarthSatellite, lat: float, lon: float, start: datetime, hours: int, min_el: float
) -> list[dict]:
    """Complete passes (rise -> culmination -> set) above min_el within the window."""
    site = wgs84.latlon(lat, lon)
    t0 = to_time(start)
    t1 = ts.tt_jd(t0.tt + hours / 24)
    times, events = sat.find_events(site, t0, t1, altitude_degrees=min_el)
    result, current = [], None
    for t, event in zip(times, events, strict=True):
        if event == 0:  # rise
            current = {"rise": t.utc_datetime(), "culmination": None, "max_elevation_deg": -90.0}
        elif event == 1 and current is not None:  # culmination: keep the highest one
            alt = float((sat - site).at(t).altaz()[0].degrees)
            if alt > current["max_elevation_deg"]:
                current["culmination"] = t.utc_datetime()
                current["max_elevation_deg"] = round(alt, 1)
        elif event == 2 and current is not None and current["culmination"] is not None:  # set
            current["set"] = t.utc_datetime()
            result.append(current)
            current = None
    return result
