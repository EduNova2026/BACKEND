from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_replica_session, get_session
from app.dependencies.auth import get_current_user, require_role
from app.models.import_job import ImportJob
from app.schemas.import_job import ImportJobOut
from app.services.import_service import run_import

router = APIRouter(prefix="/imports", tags=["imports"])

_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 Mo


@router.post(
    "/upload",
    response_model=ImportJobOut,
    status_code=status.HTTP_201_CREATED,
    summary="Importer un fichier CSV de notes Aurion",
)
async def upload_csv(
    file: UploadFile,
    enseignement_id: UUID,
    session: AsyncSession = Depends(get_session),
    replica_session: AsyncSession = Depends(get_replica_session),
    current_user: dict[str, object] = Depends(
        require_role("enseignant", "admin_pedagogique")
    ),
) -> ImportJobOut:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier doit être un .csv",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 5 Mo)",
        )

    importe_par = UUID(str(current_user["id"]))
    job = await run_import(
        content=content,
        nom_fichier=file.filename,
        enseignement_id=enseignement_id,
        importe_par=importe_par,
        session=session,
        replica_session=replica_session,
    )
    return ImportJobOut.model_validate(job)


@router.get(
    "/{job_id}",
    response_model=ImportJobOut,
    summary="Récupérer le résultat d'un import",
)
async def get_import_job(
    job_id: UUID,
    replica_session: AsyncSession = Depends(get_replica_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> ImportJobOut:
    job = await replica_session.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import introuvable",
        )
    return ImportJobOut.model_validate(job)


@router.get(
    "",
    response_model=list[ImportJobOut],
    summary="Historique des imports",
)
async def list_import_jobs(
    replica_session: AsyncSession = Depends(get_replica_session),
    current_user: dict[str, object] = Depends(get_current_user),
) -> list[ImportJobOut]:
    result = await replica_session.execute(
        select(ImportJob).order_by(ImportJob.created_at.desc()).limit(50)
    )
    return [ImportJobOut.model_validate(job) for job in result.scalars().all()]