from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import satellites, system, visibility
from app.tle_store import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load_initial()  # snapshot/cache from disk only; CelesTrak is hit lazily on first request
    yield


app = FastAPI(
    title="SatTrack",
    description="Planowanie pomiarów GNSS: widoczność satelitów GPS, Galileo, GLONASS i BeiDou.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(system.router)
app.include_router(satellites.router)
app.include_router(visibility.router)
# Mounted last so API routes win; /.auth/* never reaches the app (handled by the Easy Auth sidecar).
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
