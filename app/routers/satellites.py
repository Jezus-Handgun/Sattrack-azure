from fastapi import APIRouter

from app.models import GroupInfo
from app.tle_store import GROUPS, store

router = APIRouter(prefix="/api")


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
