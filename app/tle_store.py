"""TLE data store: in-memory cache -> CelesTrak -> cache dir file -> bundled snapshot.

CelesTrak returns HTTP 403 when the same IP re-downloads a group before it updates (~2 h),
so every group is fetched at most once per TTL, failures included, and never retried in a loop.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from skyfield.api import EarthSatellite, load

from app.config import settings

log = logging.getLogger(__name__)

ts = load.timescale(builtin=True)  # builtin=True: no downloads of time data files

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
USER_AGENT = "SatTrack/1.0 (student project)"
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "snapshot"

# app key -> (CelesTrak group, UI label)
GROUPS: dict[str, tuple[str, str]] = {
    "gps": ("gps-ops", "GPS (USA)"),
    "galileo": ("galileo", "Galileo (UE)"),
    "glonass": ("glo-ops", "GLONASS (Rosja)"),
    "beidou": ("beidou", "BeiDou (Chiny)"),
    "stations": ("stations", "Stacje kosmiczne (ISS)"),
}


@dataclass
class GroupData:
    satellites: list[EarthSatellite]
    source: str  # "live" | "cache" | "snapshot"
    fetched_at: datetime | None  # when the data came from CelesTrak; None for the snapshot

    @property
    def newest_epoch(self) -> datetime | None:
        return max((s.epoch.utc_datetime() for s in self.satellites), default=None)


class TleStore:
    def __init__(
        self,
        cache_dir: Path,
        ttl_seconds: int,
        snapshot_dir: Path = SNAPSHOT_DIR,
        client: httpx.Client | None = None,
    ):
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        self.snapshot_dir = snapshot_dir
        self.client = client or httpx.Client(timeout=5.0, follow_redirects=True)
        self._data: dict[str, GroupData] = {}
        self._last_attempt: dict[str, float] = {}  # epoch seconds of the last CelesTrak request
        self._lock = threading.Lock()

    def load_initial(self) -> None:
        """Load every group from disk, without network: cache dir file if present, else snapshot."""
        for key in GROUPS:
            cache_file = self.cache_dir / f"{key}.tle"
            if cache_file.exists():
                mtime = cache_file.stat().st_mtime
                self._data[key] = GroupData(
                    _parse(cache_file), "cache", datetime.fromtimestamp(mtime, UTC)
                )
                # The cache file counts as an attempt, so restarts within TTL don't hit CelesTrak.
                self._last_attempt[key] = mtime
            else:
                self._data[key] = GroupData(
                    _parse(self.snapshot_dir / f"{key}.tle"), "snapshot", None
                )
            data = self._data[key]
            log.info("TLE %s: %d satellites from %s", key, len(data.satellites), data.source)

    def get(self, key: str) -> GroupData:
        """Current data for a group; lazily refreshes from CelesTrak once the TTL has passed."""
        with self._lock:
            if not self._data:
                self.load_initial()
            last = self._last_attempt.get(key)
            if last is None or time.time() - last >= self.ttl:
                self._refresh(key)
            return self._data[key]

    def find(self, norad_id: int) -> tuple[str, EarthSatellite] | None:
        """Look up a satellite by NORAD ID in the data already loaded (no refresh)."""
        for key, data in self._data.items():
            for sat in data.satellites:
                if sat.model.satnum == norad_id:
                    return key, sat
        return None

    def _refresh(self, key: str) -> None:
        self._last_attempt[key] = time.time()  # set first: a failure must also wait a full TTL
        group = GROUPS[key][0]
        try:
            response = self.client.get(
                CELESTRAK_URL,
                params={"GROUP": group, "FORMAT": "tle"},
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = self.cache_dir / f"{key}.tle.tmp"
            tmp.write_text(response.text, encoding="utf-8")
            satellites = _parse(tmp)
            if not satellites:  # e.g. "No GP data found" with HTTP 200
                raise ValueError("response contains no TLE records")
            os.replace(tmp, self.cache_dir / f"{key}.tle")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            log.warning(
                "CelesTrak fetch failed for %s (%s), keeping %s data",
                key,
                exc,
                self._data[key].source,
            )
            return
        self._data[key] = GroupData(satellites, "live", datetime.now(UTC))
        log.info("CelesTrak fetch OK for %s: %d satellites", key, len(satellites))


def _parse(path: Path) -> list[EarthSatellite]:
    return load.tle_file(str(path), ts=ts)


store = TleStore(Path(settings.tle_cache_dir), settings.tle_ttl_seconds)
