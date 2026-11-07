from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GroupInfo(BaseModel):
    key: str
    label: str
    celestrak_group: str
    count: int
    source: Literal["live", "cache", "snapshot"]
    fetched_at: datetime | None  # when downloaded from CelesTrak; null for the bundled snapshot
    newest_epoch: datetime | None  # newest TLE epoch in the group


class SatellitePosition(BaseModel):
    norad_id: int
    name: str
    group: str
    lat: float
    lon: float
    alt_km: float
    speed_km_s: float


class TrackPoint(BaseModel):
    time: datetime
    lat: float
    lon: float


class SatelliteDetail(SatellitePosition):
    time: datetime
    tle_epoch: datetime
    track: list[TrackPoint]  # ±45 min, 1 min step


class VisibleSatellite(BaseModel):
    norad_id: int
    name: str
    constellation: str
    elevation_deg: float
    azimuth_deg: float


class VisibilityResponse(BaseModel):
    lat: float
    lon: float
    time: datetime
    min_elevation: float
    counts: dict[str, int]  # per constellation + "total"
    satellites: list[VisibleSatellite]


class TimelineResponse(BaseModel):
    lat: float
    lon: float
    min_elevation: float
    step_min: int
    times: list[datetime]
    counts: dict[str, list[int]]  # per constellation + "total", aligned with times


class Pass(BaseModel):
    rise: datetime
    culmination: datetime
    max_elevation_deg: float
    set: datetime


class PassesResponse(BaseModel):
    norad_id: int
    name: str
    lat: float
    lon: float
    min_elevation: float
    passes: list[Pass]
