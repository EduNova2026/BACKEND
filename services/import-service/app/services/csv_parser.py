from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field


@dataclass
class ExamenCSV:
    id_aurion: str
    code: str
    libelle: str


@dataclass
class LigneCSV:
    ligne_num: int
    id_apprenant: str
    prenom: str
    nom: str
    valeur: float | None
    appreciation: str
    absent: bool
    motif_absence: str | None


@dataclass
class ResultatParsing:
    examen: ExamenCSV | None
    lignes: list[LigneCSV] = field(default_factory=list)
    erreurs_parsing: list[str] = field(default_factory=list)


def _decode_content(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Impossible de décoder le fichier CSV")


def _parse_note(raw: str) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def parse_aurion_csv(content: bytes) -> ResultatParsing:
    text = _decode_content(content)
    reader = csv.DictReader(io.StringIO(text), delimiter=";")

    lignes: list[LigneCSV] = []
    erreurs: list[str] = []
    examen: ExamenCSV | None = None

    for i, row in enumerate(reader, start=2):  # ligne 1 = header
        try:
            if examen is None:
                examen = ExamenCSV(
                    id_aurion=row["id.Épreuve"].strip(),
                    code=row["Code.Épreuve"].strip(),
                    libelle=row["Libellé.Épreuve"].strip(),
                )

            absent = bool(row.get("id.Motif d absence", "").strip())
            valeur = None if absent else _parse_note(row.get("Note numérique", ""))

            lignes.append(LigneCSV(
                ligne_num=i,
                id_apprenant=row["id.Apprenant"].strip(),
                prenom=row["Prénom.Apprenant"].strip(),
                nom=row["Nom.Apprenant"].strip(),
                valeur=valeur,
                appreciation=row.get("Appréciation", "").strip(),
                absent=absent,
                motif_absence=row.get("Motif d absence", "").strip() or None,
            ))
        except KeyError as e:
            erreurs.append(f"Ligne {i} : colonne manquante {e}")

    return ResultatParsing(examen=examen, lignes=lignes, erreurs_parsing=erreurs)