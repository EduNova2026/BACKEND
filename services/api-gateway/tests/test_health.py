from fastapi.testclient import TestClient

from app.main import app

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
