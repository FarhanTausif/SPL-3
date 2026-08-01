import pytest
from httpx import ASGITransport, AsyncClient

from dehalu.main import create_app


@pytest.mark.asyncio
async def test_local_dev_preflight_is_allowed_on_any_port() -> None:
    transport = ASGITransport(app=create_app(create_schema_on_startup=False))

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.options(
            "/api/runs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
