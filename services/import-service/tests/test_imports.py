import pytest

from app.services.csv_parser import parse_aurion_csv

SAMPLE_CSV = b"""id.\xc9preuve;Code.\xc9preuve;Libell\xe9.\xc9preuve;id.Apprenant;Pr\xe9nom.Apprenant;Nom.Apprenant;Note num\xe9rique;Note alphanum\xe9rique;Non not\xe9;Appr\xe9ciation;id.Motif d absence;Motif d absence;intervenant_id;intervenant_nom;intervenant_prenom;id.inscription
63669102;2526_HEI_DS1_Gr456;HEI3TC Dev FrontEnd DS1;90000001;Amine;AMARI;7,07;;Faux;;;;;;;
63669102;2526_HEI_DS1_Gr456;HEI3TC Dev FrontEnd DS1;90000002;Sarah;BACHIRI;11,89;;Faux;;;;;;;
63669102;2526_HEI_DS1_Gr456;HEI3TC Dev FrontEnd DS1;90000003;Malik;ROUSSEAU;;;Faux;;46749;Absence non excus\xe9e;;;;
"""


def test_parse_aurion_csv_notes():
    resultat = parse_aurion_csv(SAMPLE_CSV)

    assert resultat.examen is not None
    assert resultat.examen.id_aurion == "63669102"
    assert resultat.examen.code == "2526_HEI_DS1_Gr456"
    assert len(resultat.lignes) == 3
    assert not resultat.erreurs_parsing


def test_parse_note_virgule():
    resultat = parse_aurion_csv(SAMPLE_CSV)
    amine = resultat.lignes[0]

    assert amine.nom == "AMARI"
    assert amine.prenom == "Amine"
    assert amine.valeur == pytest.approx(7.07)
    assert not amine.absent


def test_parse_etudiant_absent():
    resultat = parse_aurion_csv(SAMPLE_CSV)
    malik = resultat.lignes[2]

    assert malik.nom == "ROUSSEAU"
    assert malik.absent is True
    assert malik.valeur is None
    assert malik.motif_absence == "Absence non excus\xe9e"


def test_parse_csv_vide():
    resultat = parse_aurion_csv(b"")
    assert resultat.examen is None
    assert resultat.lignes == []