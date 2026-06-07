import pytest

from app.services.csv_parser import parse_aurion_csv
from app.services.import_service import create_examen_in_scolarite, create_notes_in_scolarite

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


@pytest.mark.asyncio
async def test_create_examen_in_scolarite_posts_examen_payload(monkeypatch):
    recorded_url = ""
    recorded_json = {}
    recorded_headers = {}

    class FakeResponse:
        status_code = 201
        text = ""

        def json(self):
            return {"id": "00000000-0000-0000-0000-000000000099"}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json, headers, timeout):
            nonlocal recorded_url, recorded_json, recorded_headers
            recorded_url = url
            recorded_json = json
            recorded_headers = headers
            assert timeout == 10
            return FakeResponse()

    monkeypatch.setattr("app.services.import_service.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        "app.services.import_service.settings.scolarite_service_url",
        "http://scolarite-service:8000/",
    )

    examen_id = await create_examen_in_scolarite(
        {"enseignement_id": "00000000-0000-0000-0000-000000000001", "nom": "DS1"},
        "Bearer import-token",
    )

    assert examen_id == "00000000-0000-0000-0000-000000000099"
    assert recorded_url == "http://scolarite-service:8000/api/v1/examens/"
    assert recorded_json["nom"] == "DS1"
    assert recorded_headers == {"Authorization": "Bearer import-token"}


@pytest.mark.asyncio
async def test_create_notes_in_scolarite_posts_batch_payload(monkeypatch):
    recorded_url = ""
    recorded_json = {}
    recorded_headers = {}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json, headers, timeout):
            nonlocal recorded_url, recorded_json, recorded_headers
            recorded_url = url
            recorded_json = json
            recorded_headers = headers
            assert timeout == 10
            return type("Response", (), {"status_code": 201, "text": ""})()

    monkeypatch.setattr("app.services.import_service.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        "app.services.import_service.settings.scolarite_service_url",
        "http://scolarite-service:8000/",
    )

    await create_notes_in_scolarite(
        {
            "examen_id": "00000000-0000-0000-0000-000000000099",
            "notes": [],
        },
        "Bearer import-token",
    )

    assert recorded_url == "http://scolarite-service:8000/api/v1/notes/batch"
    assert recorded_json["examen_id"] == "00000000-0000-0000-0000-000000000099"
    assert recorded_headers == {"Authorization": "Bearer import-token"}


@pytest.mark.asyncio
async def test_create_notes_in_scolarite_raises_on_upstream_error(monkeypatch):
    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json, headers, timeout):
            return type("Response", (), {"status_code": 409, "text": "duplicate"})()

    monkeypatch.setattr("app.services.import_service.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(RuntimeError, match="duplicate"):
        await create_notes_in_scolarite({}, "Bearer import-token")
