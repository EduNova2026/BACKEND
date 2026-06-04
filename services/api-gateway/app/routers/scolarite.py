"""Proxy les requetes /scolarite/* vers le scolarite-service."""

from fastapi import APIRouter, Request

from app.config import get_settings
from app.services.http_client import proxy_request

router = APIRouter(prefix="/scolarite", tags=["scolarite"])


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_scolarite(path: str, request: Request):
    settings = get_settings()
    upstream_url = f"{settings.scolarite_service_url.rstrip('/')}/{path.lstrip('/')}"
    return await proxy_request(request, upstream_url)
