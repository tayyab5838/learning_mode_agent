import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """✅ Test user registration endpoint"""
    payload = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword123"
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "testuser@example.com"

@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient):
    """❌ Test registration with duplicate username"""
    payload = {
        "username": "duplicateuser",
        "email": "user1@example.com",
        "password": "password123"
    }
    
    # First registration
    response1 = await client.post("/auth/register", json=payload)
    assert response1.status_code == 201
    
    # Second registration with same username but different email
    payload2 = {
        "username": "duplicateuser",
        "email": "user2@example.com",
        "password": "password456"
    }
    response2 = await client.post("/auth/register", json=payload2)
    assert response2.status_code == 400

@pytest.mark.asyncio
async def test_register_existing_user(client: AsyncClient):
    payload = {"username": "bob", "email": "bob@example.com", "password": "password123"}
    await client.post("/auth/register", json=payload)
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "exists" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_login_user_success(client: AsyncClient):
    payload = {"username": "charlie", "email": "charlie@example.com", "password": "mypassword"}
    await client.post("/auth/register", json=payload)
    response = await client.post("/auth/login", params={"username": "charlie", "password": "mypassword"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

@pytest.mark.asyncio
async def test_login_user_invalid_credentials(client):
    payload = {"username": "david", "email": "david@example.com", "password": "1234"}
    await client.post("/auth/register", json=payload)
    response = await client.post("/auth/login", params={"username": "david", "password": "wrong"})
    assert response.status_code == 401

async def test_complete_auth_flow(client: AsyncClient):
    """✅ Test complete authentication flow"""
    # Step 1: Register
    register_payload = {
        "username": "flowuser",
        "email": "flow@example.com",
        "password": "securepass123"
    }
    register_response = await client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 201
    user_data = register_response.json()
    
    # Step 2: Login
    login_response = await client.post(
        "/auth/login",
        params={"username": "flowuser", "password": "securepass123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Step 3: Access protected route
    me_response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["username"] == user_data["username"]
    assert me_data["id"] == user_data["id"]