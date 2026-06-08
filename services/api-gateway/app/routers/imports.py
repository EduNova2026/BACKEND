from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.config import get_settings
from app.services.http_client import proxy_request
from shared.schemas import ErrorResponse

AUTH_OPENAPI_EXTRA = {
    "parameters": [
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        }
    ]
}

router = APIRouter(
    prefix="/imports",
    tags=["imports"],
    responses={status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse}},
)


def import_url(path: str) -> str:
    settings = get_settings()
    return f"{settings.import_service_url.rstrip('/')}/api/v1/{path.lstrip('/')}"


@router.get("", include_in_schema=False)
@router.get("/", openapi_extra=AUTH_OPENAPI_EXTRA)
async def list_import_jobs(request: Request) -> Response:
    return await proxy_request(request, import_url("imports"))


@router.get(
    "/{job_id}",
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_import_job(request: Request, job_id: UUID) -> Response:
    return await proxy_request(request, import_url(f"imports/{job_id}"))


@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
async def upload_import_csv(request: Request, enseignement_id: UUID) -> Response:
    _ = enseignement_id
    return await proxy_request(request, import_url("imports/upload"))
