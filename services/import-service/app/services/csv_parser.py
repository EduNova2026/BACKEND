from __future__ import annotations

import csv
import io
import unicodedata
from dataclasses import dataclass, field


def _normalize_column_name(name: str) -> str:
    """Strip accents from column name for tolerant matching."""
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _get_row_column(row: dict[str, str], *candidates: str) -> str:
    """Return the first matching column value, trying accent-stripped fallback."""
    for col in candidates:
        if col in row:
            return row[col]
    # Fallback: try accent-stripped matching
    normalized_row = {_normalize_column_name(k): v for k, v in row.items()}
    for col in candidates:
        normalized = _normalize_column_name(col)
        if normalized in normalized_row:
            return normalized_row[normalized]
    raise KeyError(candidates[0])


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
                    id_aurion=_get_row_column(row, "id.Épreuve").strip(),
                    code=_get_row_column(row, "Code.Épreuve").strip(),
                    libelle=_get_row_column(row, "Libellé.Épreuve").strip(),
                )

            absent = bool(row.get("id.Motif d absence", "").strip())
            valeur = None if absent else _parse_note(_get_row_column(row, "Note numérique"))

            lignes.append(LigneCSV(
                ligne_num=i,
                id_apprenant=_get_row_column(row, "id.Apprenant").strip(),
                prenom=_get_row_column(row, "Prénom.Apprenant").strip(),
                nom=_get_row_column(row, "Nom.Apprenant").strip(),
                valeur=valeur,
                absent=absent,
                motif_absence=row.get("Motif d absence", "").strip() or None,
            ))
        except KeyError as e:
            erreurs.append(f"Ligne {i} : colonne manquante {e}")

    return ResultatParsing(examen=examen, lignes=lignes, erreurs_parsing=erreurs)
