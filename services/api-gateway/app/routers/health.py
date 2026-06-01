from fastapi import APIRouter

from app.config import settings
from shared.health import health_response
from shared.schemas import DetailedHealthResponse, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> dict[str, str]:
    return health_response(settings.app_name)


@router.get("/health/detailed", response_model=DetailedHealthResponse)
def detailed_health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": settings.app_version,
    }
