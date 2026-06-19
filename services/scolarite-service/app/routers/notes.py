from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from shared.schemas import ErrorResponse

from app.database import get_replica_session, get_session
from app.dependencies.auth import (
    CurrentUser,
    can_access_etudiant,
    ensure_can_access_etudiant,
    get_current_user,
    is_responsable_pedagogique,
)
from app.models import Examen, Note
from app.schemas import ExamenCreate, ExamenOut, ExamenUpdate, NoteBatchCreate, NoteCreate, NoteItemCreate, NoteOut, NoteUpdate

router = APIRouter(tags=["notes"])


def _examen_out(examen: Examen) -> ExamenOut:
    return ExamenOut.model_validate(examen)


def _note_out(note: Note) -> NoteOut:
    examen = note.examen
    return NoteOut(
        id=note.id,
        etudiant_id=note.etudiant_id,
        examen_id=note.examen_id,
        examen=_examen_out(examen),
        valeur=note.valeur,
        absent=note.absent,
        motif_absence=note.motif_absence,
        date_saisie=note.date_saisie,
        saisi_par=note.saisi_par,
    )


def _ensure_note_payload_consistent(payload: NoteItemCreate | NoteUpdate) -> None:
    absent = payload.absent
    valeur = payload.valeur
    if absent is False and valeur is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Une note non absente doit avoir une valeur",
        )


async def _get_or_create_examen(
    session: AsyncSession,
    payload: ExamenCreate,
    current_user: CurrentUser,
) -> Examen:
    if payload.code_aurion is not None:
        existing = await session.scalar(
            select(Examen).where(
                Examen.enseignement_id == payload.enseignement_id,
                Examen.code_aurion == payload.code_aurion,
            )
        )
        if existing is not None:
            return existing

    examen = Examen(
        enseignement_id=payload.enseignement_id,
        nom=payload.nom,
        type=payload.type,
        coefficient=payload.coefficient,
        note_max=payload.note_max,
        date_examen=payload.date_examen,
        code_aurion=payload.code_aurion,
        cree_par=current_user.id,
    )
    session.add(examen)
    await session.flush()
    return examen


async def _get_examen_or_404(session: AsyncSession, examen_id: UUID) -> Examen:
    examen = await session.get(Examen, examen_id)
    if examen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Examen not found")
    return examen


async def _get_note_or_404(session: AsyncSession, note_id: UUID) -> Note:
    note = await session.scalar(
        select(Note).options(selectinload(Note.examen)).where(Note.id == note_id)
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


def _build_note(item: NoteItemCreate, examen: Examen, current_user: CurrentUser) -> Note:
    return Note(
        etudiant_id=item.etudiant_id,
        examen_id=examen.id,
        valeur=item.valeur,
        absent=item.absent,
        motif_absence=item.motif_absence,
        saisi_par=current_user.id,
    )


@router.get(
    "/examens/",
    response_model=list[ExamenOut],
)
async def list_examens(
    enseignement_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[ExamenOut]:
    query = select(Examen)
    if enseignement_id is not None:
        query = query.where(Examen.enseignement_id == enseignement_id)
    examens = (await replica_session.scalars(query.offset(skip).limit(limit))).all()
    return [_examen_out(examen) for examen in examens]


@router.post(
    "/examens/",
    response_model=ExamenOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_examen(
    payload: ExamenCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExamenOut:
    examen = await _get_or_create_examen(session, payload, current_user)
    await session.commit()
    await session.refresh(examen)
    return _examen_out(examen)


@router.get(
    "/examens/{examen_id}",
    response_model=ExamenOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_examen(
    examen_id: UUID,
    replica_session: AsyncSession = Depends(get_replica_session),
) -> ExamenOut:
    examen = await _get_examen_or_404(replica_session, examen_id)
    return _examen_out(examen)


@router.patch(
    "/examens/{examen_id}",
    response_model=ExamenOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def update_examen(
    examen_id: UUID,
    payload: ExamenUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ExamenOut:
    _ = current_user
    examen = await _get_examen_or_404(session, examen_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(examen, field, value)
    await session.commit()
    await session.refresh(examen)
    return _examen_out(examen)


@router.get(
    "/notes/",
    response_model=list[NoteOut],
)
async def list_notes(
    etudiant_id: UUID | None = None,
    enseignement_id: UUID | None = None,
    examen_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> list[NoteOut]:
    query = select(Note).options(selectinload(Note.examen))
    if enseignement_id is not None:
        query = query.join(Examen).where(Examen.enseignement_id == enseignement_id)
    if etudiant_id is not None:
        await ensure_can_access_etudiant(replica_session, current_user, etudiant_id)
        query = query.where(Note.etudiant_id == etudiant_id)
    if examen_id is not None:
        query = query.where(Note.examen_id == examen_id)

    notes = (await replica_session.scalars(query.offset(skip).limit(limit))).all()
    if etudiant_id is None and not is_responsable_pedagogique(current_user):
        accessible_notes: list[Note] = []
        for note in notes:
            if await can_access_etudiant(replica_session, current_user, note.etudiant_id):
                accessible_notes.append(note)
        notes = accessible_notes
    return [_note_out(note) for note in notes]


@router.post(
    "/notes/",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def create_note(
    payload: NoteCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NoteOut:
    _ensure_note_payload_consistent(payload)
    await ensure_can_access_etudiant(session, current_user, payload.etudiant_id)
    examen = await _get_examen_or_404(session, payload.examen_id)
    note = _build_note(payload, examen, current_user)
    session.add(note)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une note existe déjà pour cet étudiant et cette évaluation",
        ) from exc
    await session.refresh(note)
    note.examen = examen
    return _note_out(note)


@router.post(
    "/notes/batch",
    response_model=list[NoteOut],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def create_notes_batch(
    payload: NoteBatchCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NoteOut]:
    if not payload.notes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le batch doit contenir au moins une note",
        )

    for item in payload.notes:
        _ensure_note_payload_consistent(item)
        await ensure_can_access_etudiant(session, current_user, item.etudiant_id)

    examen = await _get_examen_or_404(session, payload.examen_id)
    notes = [_build_note(item, examen, current_user) for item in payload.notes]
    session.add_all(notes)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une note existe déjà pour au moins un étudiant de cette évaluation",
        ) from exc

    for note in notes:
        await session.refresh(note)
        note.examen = examen
    return [_note_out(note) for note in notes]


@router.get(
    "/notes/{note_id}",
    response_model=NoteOut,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_note(
    note_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    replica_session: AsyncSession = Depends(get_replica_session),
) -> NoteOut:
    note = await _get_note_or_404(replica_session, note_id)
    await ensure_can_access_etudiant(replica_session, current_user, note.etudiant_id)
    return _note_out(note)


@router.patch(
    "/notes/{note_id}",
    response_model=NoteOut,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
async def update_note(
    note_id: UUID,
    payload: NoteUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NoteOut:
    note = await _get_note_or_404(session, note_id)
    await ensure_can_access_etudiant(session, current_user, note.etudiant_id)
    update_data = payload.model_dump(exclude_unset=True)
    candidate = NoteUpdate(
        valeur=update_data.get("valeur", note.valeur),
        absent=update_data.get("absent", note.absent),
        motif_absence=update_data.get("motif_absence", note.motif_absence),
    )
    _ensure_note_payload_consistent(candidate)
    for field, value in update_data.items():
        setattr(note, field, value)
    await session.commit()
    await session.refresh(note)
    return _note_out(note)


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def delete_note(
    note_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    note = await _get_note_or_404(session, note_id)
    await ensure_can_access_etudiant(session, current_user, note.etudiant_id)
    await session.delete(note)
    await session.commit()
