from __future__ import annotations

from uuid import UUID

import httpx
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.import_job import ImportJob
from app.models.refs import EnseignementRef
from app.services.csv_parser import parse_aurion_csv
from app.services.matcher import find_etudiant_by_nom_prenom


async def create_examen_in_scolarite(payload: dict[str, object], authorization: str) -> str:
    url = f"{settings.scolarite_service_url.rstrip('/')}/api/v1/examens/"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": authorization},
            timeout=10,
        )
    if response.status_code != status.HTTP_201_CREATED:
        raise RuntimeError(response.text)
    return str(response.json()["id"])


async def create_notes_in_scolarite(payload: dict[str, object], authorization: str) -> None:
    url = f"{settings.scolarite_service_url.rstrip('/')}/api/v1/notes/batch"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={"Authorization": authorization},
            timeout=10,
        )
    if response.status_code != status.HTTP_201_CREATED:
        raise RuntimeError(response.text)


async def run_import(
    content: bytes,
    nom_fichier: str,
    enseignement_id: UUID | None,
    examen_id: str | None,
    importe_par: UUID,
    authorization: str,
    session: AsyncSession,
    replica_session: AsyncSession,
) -> ImportJob:
    job = ImportJob(
        importe_par=importe_par,
        nom_fichier=nom_fichier,
        type_import="notes",
        statut="en_cours",
    )
    session.add(job)
    await session.flush()

    if examen_id is None:
        enseignement = await replica_session.get(EnseignementRef, enseignement_id)
        if enseignement is None:
            job.statut = "erreur"
            job.erreurs_detail = [{"raison": "enseignement_id introuvable en base"}]
            await session.commit()
            return job

    resultat = parse_aurion_csv(content)

    if resultat.examen is None:
        job.statut = "erreur"
        job.erreurs_detail = [{"raison": "Fichier CSV vide ou invalide"}]
        await session.commit()
        return job

    erreurs = list(
        {"ligne": 1, "nom": "", "prenom": "", "raison": e}
        for e in resultat.erreurs_parsing
    )
    ok = 0
    notes_payload: list[dict[str, object]] = []

    for ligne in resultat.lignes:
        etudiant_id = await find_etudiant_by_nom_prenom(
            replica_session, ligne.nom, ligne.prenom
        )

        if etudiant_id is None:
            erreurs.append({
                "ligne": ligne.ligne_num,
                "nom": ligne.nom,
                "prenom": ligne.prenom,
                "raison": "Étudiant introuvable en base",
            })
            continue

        if not ligne.absent and ligne.valeur is None:
            erreurs.append({
                "ligne": ligne.ligne_num,
                "nom": ligne.nom,
                "prenom": ligne.prenom,
                "raison": "Note manquante et étudiant non marqué absent",
            })
            continue

        if ligne.absent:
            motif = (ligne.motif_absence or "").lower()
            valeur = 0.0 if "non excus" in motif else None
        else:
            valeur = ligne.valeur

        notes_payload.append({
            "etudiant_id": str(etudiant_id),
            "valeur": valeur,
            "absent": ligne.absent,
            "motif_absence": ligne.motif_absence,
        })
        ok += 1

    if notes_payload:
        try:
            if examen_id is None:
                examen_id = await create_examen_in_scolarite(
                    {
                        "enseignement_id": str(enseignement_id),
                        "nom": resultat.examen.libelle,
                        "type": "examen",
                        "coefficient": 1.0,
                        "note_max": 20.0,
                        "code_aurion": resultat.examen.code,
                    },
                    authorization,
                )
            await create_notes_in_scolarite(
                {
                    "examen_id": examen_id,
                    "notes": notes_payload,
                },
                authorization,
            )
        except RuntimeError as exc:
            job.statut = "erreur"
            job.erreurs_detail = [{"raison": f"Création des notes impossible: {exc}"}]
            await session.commit()
            return job

    job.lignes_total = len(resultat.lignes)
    job.lignes_ok = ok
    job.lignes_erreur = len(erreurs)
    job.erreurs_detail = erreurs if erreurs else None

    if ok == 0:
        job.statut = "erreur"
    elif erreurs:
        job.statut = "erreur_partielle"
    else:
        job.statut = "succes"

    await session.commit()
    return job
