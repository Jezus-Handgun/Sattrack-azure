import logging
import time as perf
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import orbit
from app.config import settings
from app.models import PassesResponse, TimelineResponse, VisibilityResponse
from app.tle_store import store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

Lat = Annotated[float, Query(ge=-90, le=90, description="Szerokość geograficzna [°]")]
Lon = Annotated[float, Query(ge=-180, le=180, description="Długość geograficzna [°]")]
MinElevation = Annotated[float, Query(ge=0, le=90, description="Maska elewacji [°]")]


def gnss_groups():
    return {key: store.get(key).satellites for key in orbit.GNSS_GROUPS}


@router.get("/visible")
def visible(
    lat: Lat = settings.default_lat,
    lon: Lon = settings.default_lon,
    time: datetime | None = None,
    min_elevation: MinElevation = settings.min_elevation_deg,
) -> VisibilityResponse:
    when = time or datetime.now(UTC)
    sats = orbit.visible(gnss_groups(), lat, lon, when, min_elevation)
    counts = {key: 0 for key in orbit.GNSS_GROUPS}
    for s in sats:
        counts[s["constellation"]] += 1
    counts["total"] = len(sats)
    return VisibilityResponse(
        lat=lat,
        lon=lon,
        time=orbit.to_time(when).utc_datetime(),
        min_elevation=min_elevation,
        counts=counts,
        satellites=sats,
    )


@router.get("/visibility-timeline")
def visibility_timeline(
    lat: Lat = settings.default_lat,
    lon: Lon = settings.default_lon,
    hours: Annotated[int, Query(ge=1, le=48)] = 24,
    step_min: Annotated[int, Query(ge=1, le=60)] = 10,
    min_elevation: MinElevation = settings.min_elevation_deg,
) -> TimelineResponse:
    start = datetime.now(UTC).replace(second=0, microsecond=0)
    t0 = perf.perf_counter()
    times, counts = orbit.visibility_timeline(
        gnss_groups(), lat, lon, start, hours, step_min, min_elevation
    )
    log.info(
        "visibility-timeline lat=%.2f lon=%.2f hours=%d step=%d computed in %.0f ms",
        lat,
        lon,
        hours,
        step_min,
        (perf.perf_counter() - t0) * 1000,
    )
    return TimelineResponse(
        lat=lat,
        lon=lon,
        min_elevation=min_elevation,
        step_min=step_min,
        times=times,
        counts=counts,
    )


@router.get("/passes/{norad_id}")
def passes(
    norad_id: int,
    lat: Lat = settings.default_lat,
    lon: Lon = settings.default_lon,
    hours: Annotated[int, Query(ge=1, le=72)] = 48,
    min_elevation: MinElevation = settings.min_elevation_deg,
) -> PassesResponse:
    found = store.find(norad_id)
    if not found:
        raise HTTPException(404, f"Satellite {norad_id} not found")
    sat = found[1]
    return PassesResponse(
        norad_id=norad_id,
        name=sat.name,
        lat=lat,
        lon=lon,
        min_elevation=min_elevation,
        passes=orbit.passes(sat, lat, lon, datetime.now(UTC), hours, min_elevation),
    )
