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
    EnseignantGroupeOut,
    ExamenCreate,
    ExamenOut,
    GroupeCreate,
    GroupeOut,
    GroupeUpdate,
    NoteBatchCreate,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    PromotionCreate,
    PromotionOut,
    PromotionUpdate,
    ResponsablePromotionOut,
    RoleAssignmentCreate,
    RoleOut,
    UserActivationUpdate,
    UserOut,
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


@router.delete(
    "/etudiants/{etudiant_id}/promotion",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_etudiant_from_promotion(request: Request, etudiant_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"etudiants/{etudiant_id}/promotion"))


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
    "/notes",
    include_in_schema=False,
)
@router.get(
    "/notes/",
    response_model=list[NoteOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_notes(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("notes/"))


@router.get(
    "/examens",
    include_in_schema=False,
)
@router.get(
    "/examens/",
    response_model=list[ExamenOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_examens(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("examens/"))


@router.post(
    "/examens",
    include_in_schema=False,
)
@router.post(
    "/examens/",
    response_model=ExamenOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def create_examen(request: Request, payload: ExamenCreate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url("examens/"))


@router.get(
    "/examens/{examen_id}",
    response_model=ExamenOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_examen(request: Request, examen_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"examens/{examen_id}"))


@router.post(
    "/notes",
    include_in_schema=False,
)
@router.post(
    "/notes/",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def create_note(request: Request, payload: NoteCreate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url("notes/"))


@router.post(
    "/notes/batch",
    response_model=list[NoteOut],
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
async def create_notes_batch(request: Request, payload: NoteBatchCreate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url("notes/batch"))


@router.get(
    "/notes/{note_id}",
    response_model=NoteOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_note(request: Request, note_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"notes/{note_id}"))


@router.patch(
    "/notes/{note_id}",
    response_model=NoteOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def update_note(request: Request, note_id: UUID, payload: NoteUpdate) -> Response:
    _ = payload
    return await proxy_request(request, scolarite_url(f"notes/{note_id}"))


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_note(request: Request, note_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"notes/{note_id}"))


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


@router.post(
    "/groupes/{groupe_id}/enseignants/{enseignant_id}",
    response_model=EnseignantGroupeOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def assign_enseignant_to_groupe(
    request: Request,
    groupe_id: UUID,
    enseignant_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"groupes/{groupe_id}/enseignants/{enseignant_id}"),
    )


@router.get(
    "/groupes/{groupe_id}/enseignants",
    response_model=list[EnseignantGroupeOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_groupe_enseignants(request: Request, groupe_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"groupes/{groupe_id}/enseignants"))


@router.delete(
    "/groupes/{groupe_id}/enseignants/{enseignant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_enseignant_from_groupe(
    request: Request,
    groupe_id: UUID,
    enseignant_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"groupes/{groupe_id}/enseignants/{enseignant_id}"),
    )


@router.get(
    "/enseignants/{enseignant_id}/groupes",
    response_model=list[EnseignantGroupeOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_enseignant_groupes(request: Request, enseignant_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"enseignants/{enseignant_id}/groupes"))


@router.post(
    "/promotions/{promotion_id}/responsables/{responsable_id}",
    response_model=ResponsablePromotionOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}},
)
async def assign_responsable_to_promotion(
    request: Request,
    promotion_id: UUID,
    responsable_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"promotions/{promotion_id}/responsables/{responsable_id}"),
    )


@router.get(
    "/promotions/{promotion_id}/responsables",
    response_model=list[ResponsablePromotionOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def list_promotion_responsables(request: Request, promotion_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"promotions/{promotion_id}/responsables"))


@router.delete(
    "/promotions/{promotion_id}/responsables/{responsable_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def remove_responsable_from_promotion(
    request: Request,
    promotion_id: UUID,
    responsable_id: UUID,
) -> Response:
    return await proxy_request(
        request,
        scolarite_url(f"promotions/{promotion_id}/responsables/{responsable_id}"),
    )


@router.get(
    "/responsables/{responsable_id}/promotions",
    response_model=list[ResponsablePromotionOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_responsable_promotions(request: Request, responsable_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"responsables/{responsable_id}/promotions"))


@router.get(
    "/utilisateurs",
    include_in_schema=False,
)
@router.get(
    "/utilisateurs/",
    response_model=list[UserOut],
    openapi_extra=AUTH_OPENAPI_EXTRA,
)
async def list_utilisateurs(request: Request) -> Response:
    return await proxy_request(request, scolarite_url("utilisateurs/"))


@router.get(
    "/utilisateurs/{utilisateur_id}",
    response_model=UserOut,
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_utilisateur(request: Request, utilisateur_id: UUID) -> Response:
    return await proxy_request(request, scolarite_url(f"utilisateurs/{utilisateur_id}"))


@router.patch(
    "/utilisateurs/{utilisateur_id}/activation",
    response_model=dict[str, UUID | bool],
    openapi_extra=AUTH_OPENAPI_EXTRA,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def update_utilisateur_activation(
    request: Request,
    utilisateur_id: UUID,
    payload: UserActivationUpdate,
) -> Response:
    _ = payload
    return await proxy_request(
        request,
        scolarite_url(f"utilisateurs/{utilisateur_id}/activation"),
    )


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def proxy_scolarite(path: str, request: Request) -> Response:
    return await proxy_request(request, scolarite_url(path))
