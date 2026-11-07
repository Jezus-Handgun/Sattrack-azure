import html
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.auth import current_user, is_allowed
from app.config import settings
from app.routers import satellites, system, visibility
from app.tle_store import store

# stdout is collected by Container Apps into Log Analytics (ContainerAppConsoleLogs_CL).
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("SatTrack starting (TLE TTL %d s, cache dir %s)", store.ttl, store.cache_dir)
    log.info("Allowed users: %s", settings.allowed_users or "any signed-in user")
    store.load_initial()  # snapshot/cache from disk only; CelesTrak is hit lazily on first request
    yield
    log.info("SatTrack stopping")


app = FastAPI(
    title="SatTrack",
    description="Planowanie pomiarów GNSS: widoczność satelitów GPS, Galileo, GLONASS i BeiDou.",
    version="0.1.0",
    lifespan=lifespan,
)

DENIED_PAGE = """<!doctype html><html lang="pl"><meta charset="utf-8"><title>Brak dostępu</title>
<body style="font-family:system-ui;background:#0a0f1c;color:#e5e7eb;text-align:center;padding:4rem">
<h1>Brak dostępu do SatTrack</h1>
<p>Konto <b>{login}</b> nie jest na liście użytkowników tej aplikacji.</p>
<p><a href="/.auth/logout" style="color:#93c5fd">Wyloguj się</a> i zaloguj innym kontem.</p>
</body></html>"""


@app.middleware("http")
async def allow_list(request: Request, call_next):
    # Authorization on top of Easy Auth: the identity provider proves who you are, this decides
    # whether you may use the app (needed for providers like GitHub, which admit any account).
    login = current_user(request)["login"]
    if not is_allowed(login, settings.allowed_users):
        log.warning("Access denied for %s %s", login, request.url.path)
        return HTMLResponse(DENIED_PAGE.format(login=html.escape(login)), status_code=403)
    return await call_next(request)


app.include_router(system.router)
app.include_router(satellites.router)
app.include_router(visibility.router)
# Mounted last so API routes win; /.auth/* never reaches the app (handled by the Easy Auth sidecar).
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="static")
