from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.get("/status")
def gateway_status() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
