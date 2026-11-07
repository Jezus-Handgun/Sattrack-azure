from fastapi import FastAPI

from app.routers import system

app = FastAPI(
    title="SatTrack",
    description="Planowanie pomiarów GNSS: widoczność satelitów GPS, Galileo, GLONASS i BeiDou.",
    version="0.1.0",
)

app.include_router(system.router)
