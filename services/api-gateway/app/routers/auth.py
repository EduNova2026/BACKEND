from fastapi import APIRouter, Request, Response

from app.config import settings
from app.services.http_client import proxy_request


router = APIRouter(prefix="/auth", tags=["auth"])


def identity_auth_url(path: str) -> str:
    return f"{settings.identity_service_url.rstrip('/')}/api/v1/auth/{path.lstrip('/')}"


@router.post("/login")
async def login(request: Request) -> Response:
    return await proxy_request(request, identity_auth_url("login"))


@router.post("/logout")
async def logout(request: Request) -> Response:
    return await proxy_request(request, identity_auth_url("logout"))


@router.get("/me")
async def me(request: Request) -> Response:
    return await proxy_request(request, identity_auth_url("me"))


@router.post("/refresh")
async def refresh(request: Request) -> Response:
    return await proxy_request(request, identity_auth_url("refresh"))
