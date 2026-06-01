from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.config import settings
from app.main import app, create_app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "api-gateway",
    }


def test_detailed_health_check() -> None:
    response = client.get("/health/detailed")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "api-gateway",
        "environment": "development",
        "version": "0.1.0",
    }


def test_gateway_status() -> None:
    response = client.get("/api/v1/gateway/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "api-gateway",
        "version": "0.1.0",
    }


def test_openapi_is_disabled_in_production(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")

    production_app = create_app()

    assert production_app.openapi_url is None
