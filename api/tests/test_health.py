import pytest
from httpx import AsyncClient


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_returns_ok_when_database_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/health", "/health/ready"])
async def test_health_endpoints_answer_head_requests(client: AsyncClient, path: str) -> None:
    response = await client.head(path)

    assert response.status_code == 200
