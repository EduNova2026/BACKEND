"""Proxy les requetes /scolarite/* vers le scolarite-service."""

from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from app.config import get_settings
from app.services.http_client import proxy_request
from shared.schemas import (
    ErrorResponse,
    EtudiantCreate,
    EtudiantGroupeOut,
    EtudiantOut,
    EtudiantSearchResponse,
    EtudiantUpdate,
    GroupeCreate,
    GroupeOut,
    GroupeUpdate,
    PromotionCreate,
    PromotionOut,
    PromotionUpdate,
    RoleAssignmentCreate,
    RoleOut,
    UtilisateurRoleOut,
)

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
    prefix="/scolarite",
    tags=["scolarite"],
    responses={status.HTTP_502_BAD_GATEWAY: {"model": ErrorResponse}},
)


def scolarite_url(path: str) -> str:
    settings = get_settings()
    return f"{settings.scolarite_service_url.rstrip('/')}/api/v1/{path.lstrip('/')}"


@router.get(
    "/promotions",
    include_in_schema=False,
)
@router.get(
    "/promotions/",
    response_model=list[PromotionOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_promotions(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("promotions/"))


@router.post(
    "/promotions",
    include_in_schema=False,
)
@router.post(
    "/promotions/",
    response_model=PromotionOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def create_promotion(request: Request, payload: PromotionCreate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url("promotions/"))


@router.get(
    "/promotions/{promotion_id}",
    response_model=PromotionOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_promotion(request: Request, promotion_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"promotions/{promotion_id}"))


@router.patch(
    "/promotions/{promotion_id}",
    response_model=PromotionOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_promotion(
    request: Request,
    promotion_id: UUID,
    payload: PromotionUpdate,
) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url(f"promotions/{promotion_id}"))


@router.delete(
    "/promotions/{promotion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_promotion(request: Request, promotion_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"promotions/{promotion_id}"))


@router.get(
    "/promotions/{promotion_id}/groupes",
    response_model=list[GroupeOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_groupes(request: Request, promotion_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"promotions/{promotion_id}/groupes"))


@router.get(
    "/promotions/{promotion_id}/etudiants",
    response_model=list[EtudiantOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_etudiants(request: Request, promotion_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"promotions/{promotion_id}/etudiants"))


@router.post(
    "/promotions/{promotion_id}/etudiants/{etudiant_id}",
    response_model=EtudiantOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def enroll_etudiant_in_promotion(
    request: Request,
    promotion_id: UUID,
    etudiant_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"promotions/{promotion_id}/etudiants/{etudiant_id}"),
    )


@router.delete(
    "/promotions/{promotion_id}/etudiants/{etudiant_id}",
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def unenroll_etudiant_from_promotion(
    request: Request,
    promotion_id: UUID,
    etudiant_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"promotions/{promotion_id}/etudiants/{etudiant_id}"),
    )


@router.get(
    "/groupes",
    include_in_schema=False,
)
@router.get(
    "/groupes/",
    response_model=list[GroupeOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_groupes(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("groupes/"))


@router.post(
    "/groupes",
    include_in_schema=False,
)
@router.post(
    "/groupes/",
    response_model=GroupeOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def create_groupe(request: Request, payload: GroupeCreate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url("groupes/"))


@router.get(
    "/groupes/{groupe_id}",
    response_model=GroupeOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_groupe(request: Request, groupe_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"groupes/{groupe_id}"))


@router.patch(
    "/groupes/{groupe_id}",
    response_model=GroupeOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def update_groupe(request: Request, groupe_id: UUID, payload: GroupeUpdate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url(f"groupes/{groupe_id}"))


@router.delete(
    "/groupes/{groupe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_groupe(request: Request, groupe_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"groupes/{groupe_id}"))


@router.get(
    "/groupes/{groupe_id}/etudiants",
    response_model=list[EtudiantOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_groupe_etudiants(request: Request, groupe_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"groupes/{groupe_id}/etudiants"))


@router.get(
    "/etudiants",
    include_in_schema=False,
)
@router.get(
    "/etudiants/",
    response_model=list[EtudiantOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_etudiants(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("etudiants/"))


@router.post(
    "/etudiants",
    include_in_schema=False,
)
@router.post(
    "/etudiants/",
    response_model=EtudiantOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def create_etudiant(request: Request, payload: EtudiantCreate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url("etudiants/"))


@router.get(
    "/etudiants/search",
    response_model=EtudiantSearchResponse,
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def search_etudiants(request: Request, promotion_id: UUID, nom: str, prenom: str) -> Response:
    return await proxy_request(request, scolarite_url("etudiants/search"))


@router.get(
    "/etudiants/resolve",
    response_model=EtudiantOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def resolve_etudiant(request: Request, promotion_id: UUID, nom: str, prenom: str) -> Response:
    return await proxy_request(request, scolarite_url("etudiants/resolve"))


@router.get(
    "/etudiants/{etudiant_id}",
    response_model=EtudiantOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_etudiant(request: Request, etudiant_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"etudiants/{etudiant_id}"))


@router.patch(
    "/etudiants/{etudiant_id}",
    response_model=EtudiantOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def update_etudiant(
    request: Request,
    etudiant_id: UUID,
    payload: EtudiantUpdate,
) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url(f"etudiants/{etudiant_id}"))


@router.delete(
    "/etudiants/{etudiant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_etudiant(request: Request, etudiant_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"etudiants/{etudiant_id}"))


@router.get(
    "/etudiants/{etudiant_id}/groupes",
    response_model=list[GroupeOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_etudiant_groupes(request: Request, etudiant_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"etudiants/{etudiant_id}/groupes"))


@router.post(
    "/etudiants/{etudiant_id}/groupes/{groupe_id}",
    response_model=EtudiantGroupeOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
)
async def add_etudiant_to_groupe(request: Request, etudiant_id: UUID, groupe_id: UUID) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"etudiants/{etudiant_id}/groupes/{groupe_id}"),
    )


@router.delete(
    "/etudiants/{etudiant_id}/groupes/{groupe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_etudiant_from_groupe(
    request: Request,
    etudiant_id: UUID,
    groupe_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"etudiants/{etudiant_id}/groupes/{groupe_id}"),
    )


@router.get(
    "/roles",
    include_in_schema=False,
)
@router.get(
    "/roles/",
    response_model=list[RoleOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_roles(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("roles/"))


@router.get(
    "/roles/utilisateurs/{utilisateur_id}/roles",
    response_model=list[UtilisateurRoleOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_utilisateur_roles(request: Request, utilisateur_id: UUID) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"roles/utilisateurs/{utilisateur_id}/roles"),
    )


@router.post(
    "/roles/utilisateurs/{utilisateur_id}/roles",
    response_model=UtilisateurRoleOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def assign_role_to_utilisateur(
    request: Request,
    utilisateur_id: UUID,
    payload: RoleAssignmentCreate,
) -> Response:
    _ = payload
    return await proxy_request(
        request,
        scolarite_url(f"roles/utilisateurs/{utilisateur_id}/roles"),
    )


@router.delete(
    "/roles/utilisateurs/{utilisateur_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_role_from_utilisateur(
    request: Request,
    utilisateur_id: UUID,
    role_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"roles/utilisateurs/{utilisateur_id}/roles/{role_id}"),
    )


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy_scolarite(path: str, request: Request) -> Response:
    return await proxy_request(request, scolarite_url(path))
