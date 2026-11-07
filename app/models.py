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
