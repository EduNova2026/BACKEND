from fastapi import APIRouter

from app.config import settings
from shared.health import health_response

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return health_response(settings.app_name)


@router.get("/health/detailed")
def detailed_health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": settings.app_version,
    }
