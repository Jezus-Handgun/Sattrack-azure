from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    # Container Apps health probe: must stay cheap, no orbit computations here.
    return {"status": "ok"}
