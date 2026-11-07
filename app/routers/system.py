from fastapi import APIRouter, Request

from app.auth import current_user
from app.models import UserInfo

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    # Container Apps health probe: must stay cheap, no orbit computations here.
    return {"status": "ok"}


@router.get("/api/me")
def me(request: Request) -> UserInfo:
    return UserInfo(**current_user(request))
