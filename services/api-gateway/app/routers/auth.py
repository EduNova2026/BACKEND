from fastapi import APIRouter, Request, Response, status

from app.config import settings
from app.services.http_client import proxy_request
from shared.schemas import ErrorResponse, LoginRequest, LoginResponse, RefreshRequest, RefreshResponse, UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


def identity_auth_url(path: str) -> str:
    return f"{settings.identity_service_url.rstrip('/')}/api/v1/auth/{path.lstrip('/')}"


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse}},
)
async def login(request: Request, payload: LoginRequest) -> Response:
    _ = payload
    return await proxy_request(request, identity_auth_url("login"))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra={
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
    },
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
)
async def logout(request: Request) -> Response:
    return await proxy_request(request, identity_auth_url("logout"))


@router.get(
    "/me",
    response_model=UserOut,
    openapi_extra={
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
    },
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
)
async def me(request: Request) -> Response:
    return await proxy_request(request, identity_auth_url("me"))


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse},
    },
)
async def refresh(request: Request, payload: RefreshRequest) -> Response:
    _ = payload
    return await proxy_request(request, identity_auth_url("refresh"))
