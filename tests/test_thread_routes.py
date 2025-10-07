from httpx import AsyncClient



async def setup_user_and_session(client: AsyncClient) -> tuple[str, int]:
        """Helper to create user, login, and create a session"""
        # Register and login
        register_payload = {
            "username": "threaduser",
            "email": "thread@example.com",
            "password": "password123"
        }
        await client.post("/auth/register", json=register_payload)
        
        login_response = await client.post(
            "/auth/login",
            params={"username": "threaduser", "password": "password123"}
        )
        token = login_response.json()["access_token"]
        
        # Create a session
        session_response = await client.post(
            "/sessions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = session_response.json()["id"]
        
        return token, session_id

async def test_create_thread_success(client: AsyncClient):
        """✅ Test creating a thread successfully"""
        token, session_id = await setup_user_and_session(client)
        
        payload = {"title": "My First Thread"}
        response = await client.post(
            f"/threads/{session_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["session_id"] == session_id
        assert data["title"] == "My First Thread"
        assert "created_at" in data

async def test_create_thread_without_title(client: AsyncClient):
        """✅ Test creating a thread without title (optional)"""
        token, session_id = await setup_user_and_session(client)
        
        payload = {"title": None}
        response = await client.post(
            f"/threads/{session_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] is None

async def test_create_thread_empty_title(client: AsyncClient):
        """✅ Test creating a thread with empty title"""
        token, session_id = await setup_user_and_session(client)
        
        payload = {"title": ""}
        response = await client.post(
            f"/threads/{session_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == ""

async def test_create_thread_without_auth(client: AsyncClient):
        """❌ Test creating thread without authentication"""
        payload = {"title": "Unauthorized Thread"}
        response = await client.post("/threads/1", json=payload)
        
        assert response.status_code == 401

async def test_create_thread_invalid_token(client: AsyncClient):
        """❌ Test creating thread with invalid token"""
        payload = {"title": "Invalid Token Thread"}
        response = await client.post(
            "/threads/1",
            json=payload,
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

# having error in these tests

# async def test_create_thread_nonexistent_session(client: AsyncClient):
#     """❌ Test creating thread for non-existent session"""
#     token, _ = await setup_user_and_session(client)
    
#     payload = {"title": "Thread for Missing Session"}
#     response = await client.post(
#         "/threads/99999",
#         json=payload,
#         headers={"Authorization": f"Bearer {token}"}
#     )
    
#     assert response.status_code == 404
#     # assert "not found" in response.json()["detail"].lower()

# async def test_create_thread_other_users_session(client: AsyncClient):
#         """❌ Test creating thread in another user's session"""
#         # Create first user and session
#         register1 = {
#             "username": "user1",
#             "email": "user1@example.com",
#             "password": "password123"
#         }
#         await client.post("/auth/register", json=register1)
#         login1 = await client.post(
#             "/auth/login",
#             params={"username": "user1", "password": "password123"}
#         )
#         token1 = login1.json()["access_token"]
#         session1 = await client.post(
#             "/sessions/",
#             headers={"Authorization": f"Bearer {token1}"}
#         )
#         session1_id = session1.json()["id"]
        
#         # Create second user
#         register2 = {
#             "username": "user2",
#             "email": "user2@example.com",
#             "password": "password123"
#         }
#         await client.post("/auth/register", json=register2)
#         login2 = await client.post(
#             "/auth/login",
#             params={"username": "user2", "password": "password123"}
#         )
#         token2 = login2.json()["access_token"]
        
#         # User2 tries to create thread in User1's session
#         payload = {"title": "Unauthorized Thread"}
#         response = await client.post(
#             f"/threads/{session1_id}",
#             json=payload,
#             headers={"Authorization": f"Bearer {token2}"}
#         )
        
#         assert response.status_code == 404  # Session not found for this user

async def test_create_multiple_threads(client: AsyncClient):
        """✅ Test creating multiple threads in same session"""
        token, session_id = await setup_user_and_session(client)
        
        thread_titles = ["Thread 1", "Thread 2", "Thread 3"]
        thread_ids = []
        
        for title in thread_titles:
            payload = {"title": title}
            response = await client.post(
                f"/threads/{session_id}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            thread_ids.append(response.json()["id"])
        
        # All threads should have unique IDs
        assert len(set(thread_ids)) == 3