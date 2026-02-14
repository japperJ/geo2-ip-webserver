import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.anyio
async def test_login_invalid_credentials_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": "nope", "password": "bad"}
        )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect username or password"

@pytest.mark.anyio
async def test_refresh_invalid_token_type_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert resp.status_code == 401

@pytest.mark.anyio
async def test_register_duplicate_username_returns_409():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Assume admin user exists
        resp = await client.post(
            "/api/auth/register",
            json={"username": "admin", "password": "test123", "email": "admin@example.com"}
        )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()

@pytest.mark.anyio
async def test_me_invalid_token_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
    assert resp.status_code == 401

@pytest.mark.anyio
async def test_me_missing_token_returns_401():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
