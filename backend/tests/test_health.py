import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_health_check_reports_components(client: AsyncClient):
    response = await client.get("/health/")
    data = response.json()
    assert "db" in data
    assert "redis" in data
    assert data["db"] == "ok"
