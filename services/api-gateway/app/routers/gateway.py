from fastapi import APIRouter

from app.config import settings
from shared.schemas import GatewayStatusResponse

router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.get("/status", response_model=GatewayStatusResponse)
def gateway_status() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
