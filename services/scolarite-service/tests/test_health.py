import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_health_returns_service_status(async_client: AsyncClient) -> None:
    resp = await async_client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "scolarite-service"}
