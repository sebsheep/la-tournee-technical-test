from httpx import AsyncClient

from app.main import app


async def test_order_dispatchs_returns_200(client: AsyncClient):
    response = await client.post(
        app.url_path_for("dispatch"),
        json=[],
    )
    assert response.status_code == 200
