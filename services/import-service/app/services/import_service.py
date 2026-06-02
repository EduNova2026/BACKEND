from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.examen import Examen
from app.models.import_job import ImportJob
from app.models.note import Note
from app.models.refs import EnseignementRef
from app.services.csv_parser import parse_aurion_csv
from app.services.matcher import find_etudiant_by_nom_prenom


async def run_import(
    content: bytes,
    nom_fichier: str,
    enseignement_id: UUID,
    importe_par: UUID,
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

    examen = Examen(
        enseignement_id=enseignement_id,
        nom=resultat.examen.libelle,
        type="examen",
        code_aurion=resultat.examen.code,
        cree_par=importe_par,
    )
    session.add(examen)
    await session.flush()

    erreurs = list(
        {"ligne": 1, "nom": "", "prenom": "", "raison": e}
        for e in resultat.erreurs_parsing
    )
    ok = 0

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

        note = Note(
            etudiant_id=etudiant_id,
            examen_id=examen.id,
            matiere_id=enseignement.matiere_id,
            valeur=valeur,
            absent=ligne.absent,
            motif_absence=ligne.motif_absence,
            appreciation=ligne.appreciation or None,
            saisi_par=importe_par,
        )
        session.add(note)
        ok += 1

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