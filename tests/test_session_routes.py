from httpx import AsyncClient


# Helper Method
async def get_auth_token(client: AsyncClient) -> str:
        """Helper to register and login a user, returning auth token"""
        # Register user
        register_payload = {
            "username": "sessionuser",
            "email": "session@example.com",
            "password": "password123"
        }
        await client.post("/auth/register", json=register_payload)
        
        # Login
        login_response = await client.post(
            "/auth/login",
            params={"username": "sessionuser", "password": "password123"}
        )
        return login_response.json()["access_token"]

async def test_create_session_success(client: AsyncClient):
        """✅ Test creating a session with authentication"""
        token = await get_auth_token(client)
        
        response = await client.post(
            "/sessions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
        assert data["agent_type"] is None


async def test_create_session_with_agent_type(client: AsyncClient):
        """✅ Test creating a session with specific agent type"""
        token = await get_auth_token(client)
        
        response = await client.post(
            "/sessions/?agent_type=learning_mode",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["agent_type"] == "learning_mode"

async def test_create_session_without_auth(client: AsyncClient):
        """❌ Test creating session without authentication"""
        response = await client.post("/sessions/")
        
        assert response.status_code == 401

async def test_create_session_invalid_token(client: AsyncClient):
    """❌ Test creating session with invalid token"""
    response = await client.post(
        "/sessions/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401

async def test_create_multiple_sessions(client: AsyncClient):
        """✅ Test creating multiple sessions for same user"""
        token = await get_auth_token(client)
        
        # Create 3 sessions
        session_ids = []
        for i in range(3):
            response = await client.post(
                f"/sessions/?agent_type=agent_{i}",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 201
            session_ids.append(response.json()["id"])
        
        # All sessions should have different IDs
        assert len(set(session_ids)) == 3

async def test_list_sessions_empty(client: AsyncClient):
        """✅ Test listing sessions when user has none"""
        token = await get_auth_token(client)
        
        response = await client.get(
            "/sessions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

async def test_list_sessions_with_data(client: AsyncClient):
        """✅ Test listing sessions when user has sessions"""
        token = await get_auth_token(client)
        
        # Create 3 sessions
        for i in range(3):
            await client.post(
                f"/sessions/?agent_type=agent_{i}",
                headers={"Authorization": f"Bearer {token}"}
            )
        
        # List sessions
        response = await client.get(
            "/sessions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        
        # Verify structure of each session
        for session in data:
            assert "id" in session
            assert "user_id" in session
            assert "agent_type" in session
            assert "created_at" in session

async def test_list_sessions_without_auth(client: AsyncClient):
        """❌ Test listing sessions without authentication"""
        response = await client.get("/sessions/")
        
        assert response.status_code == 401

async def test_list_sessions_invalid_token(client: AsyncClient):
        """❌ Test listing sessions with invalid token"""
        response = await client.get(
            "/sessions/",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

async def test_list_sessions_user_isolation(client: AsyncClient):
        """✅ Test that users can only see their own sessions"""
        # Create first user and sessions
        register1 = {
            "username": "user1",
            "email": "user1@example.com",
            "password": "password123"
        }
        await client.post("/auth/register", json=register1)
        login1 = await client.post(
            "/auth/login",
            params={"username": "user1", "password": "password123"}
        )
        token1 = login1.json()["access_token"]
        
        # Create 2 sessions for user1
        await client.post("/sessions/", headers={"Authorization": f"Bearer {token1}"})
        await client.post("/sessions/", headers={"Authorization": f"Bearer {token1}"})
        
        # Create second user and sessions
        register2 = {
            "username": "user2",
            "email": "user2@example.com",
            "password": "password123"
        }
        await client.post("/auth/register", json=register2)
        login2 = await client.post(
            "/auth/login",
            params={"username": "user2", "password": "password123"}
        )
        token2 = login2.json()["access_token"]
        
        # Create 3 sessions for user2
        await client.post("/sessions/", headers={"Authorization": f"Bearer {token2}"})
        await client.post("/sessions/", headers={"Authorization": f"Bearer {token2}"})
        await client.post("/sessions/", headers={"Authorization": f"Bearer {token2}"})
        
        # User1 should see only 2 sessions
        response1 = await client.get(
            "/sessions/",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert len(response1.json()) == 2
        
        # User2 should see only 3 sessions
        response2 = await client.get(
            "/sessions/",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert len(response2.json()) == 3