from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, HTTPException

from app import orbit
from app.models import GroupInfo, SatelliteDetail, SatellitePosition
from app.tle_store import GROUPS, store

router = APIRouter(prefix="/api")

GroupKey = StrEnum("GroupKey", {key: key for key in GROUPS})


@router.get("/groups")
def groups() -> list[GroupInfo]:
    result = []
    for key, (celestrak_group, label) in GROUPS.items():
        data = store.get(key)
        result.append(
            GroupInfo(
                key=key,
                label=label,
                celestrak_group=celestrak_group,
                count=len(data.satellites),
                source=data.source,
                fetched_at=data.fetched_at,
                newest_epoch=data.newest_epoch,
            )
        )
    return result


@router.get("/satellites")
def satellites(group: GroupKey = GroupKey.gps) -> list[SatellitePosition]:
    now = datetime.now(UTC)
    positions = (orbit.position(sat, now) for sat in store.get(group).satellites)
    return [SatellitePosition(group=group, **p) for p in positions if p is not None]


@router.get("/satellites/{norad_id}")
def satellite_detail(norad_id: int) -> SatelliteDetail:
    found = store.find(norad_id)
    now = datetime.now(UTC)
    p = found and orbit.position(found[1], now)
    if not p:
        raise HTTPException(404, f"Satellite {norad_id} not found")
    group, sat = found
    return SatelliteDetail(
        group=group,
        time=now,
        tle_epoch=sat.epoch.utc_datetime(),
        track=orbit.ground_track(sat, now),
        **p,
    )
