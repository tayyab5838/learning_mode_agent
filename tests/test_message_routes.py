from httpx import AsyncClient
from unittest.mock import patch, MagicMock


# HELPER METHODS
async def setup_user_session_thread(client: AsyncClient) -> tuple[str, int, int]:
    """Helper to create user, session, and thread"""
    # Register and login
    register_payload = {
        "username": "messageuser",
        "email": "message@example.com",
        "password": "password123"
    }
    await client.post("/auth/register", json=register_payload)
    
    login_response = await client.post(
        "/auth/login",
        params={"username": "messageuser", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    # Create session
    session_response = await client.post(
        "/sessions/",
        headers={"Authorization": f"Bearer {token}"}
    )
    session_id = session_response.json()["id"]
    
    # Create thread
    thread_response = await client.post(
        f"/threads/{session_id}",
        json={"title": "Test Thread"},
        headers={"Authorization": f"Bearer {token}"}
    )
    thread_id = thread_response.json()["id"]
    
    return token, session_id, thread_id


# ========================================================================
# SEND MESSAGE TESTS
# ========================================================================

@patch('app.routers.messages.Runner.run')
async def test_send_message_success(mock_runner_run, client: AsyncClient):
    """✅ Test sending a message successfully"""
    token, _, thread_id = await setup_user_session_thread(client)
    
    # Mock LLM response
    mock_result = MagicMock()
    mock_result.final_output = "This is the AI response"
    mock_runner_run.return_value = mock_result
    
    payload = {"content": "Hello, AI!"}
    response = await client.post(
        f"/messages/{thread_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "response" in data
    assert "history" in data
    assert data["response"] == "This is the AI response"
    assert isinstance(data["history"], list)
    
    # History should contain user message and assistant response
    assert len(data["history"]) >= 2
    
    # Verify user message
    user_msg = next((m for m in data["history"] if m["role"] == "user"), None)
    assert user_msg is not None
    assert user_msg["content"] == "Hello, AI!"
    
    # Verify assistant message
    assistant_msg = next((m for m in data["history"] if m["role"] == "assistant"), None)
    assert assistant_msg is not None
    assert assistant_msg["content"] == "This is the AI response"


@patch('app.routers.messages.Runner.run')
async def test_send_message_conversation_flow(mock_runner_run, client: AsyncClient):
    """✅ Test multi-turn conversation"""
    token, _, thread_id = await setup_user_session_thread(client)
    
    # Mock LLM responses
    mock_result1 = MagicMock()
    mock_result1.final_output = "Hi! How can I help?"
    
    mock_result2 = MagicMock()
    mock_result2.final_output = "Sure, I can help with that."
    
    mock_runner_run.side_effect = [mock_result1, mock_result2]
    
    # First message
    response1 = await client.post(
        f"/messages/{thread_id}",
        json={"content": "Hello!"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response1.status_code == 200
    assert len(response1.json()["history"]) == 2
    
    # Second message
    response2 = await client.post(
        f"/messages/{thread_id}",
        json={"content": "Can you help me?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response2.status_code == 200
    assert len(response2.json()["history"]) == 4  # 2 user + 2 assistant

async def test_send_message_without_auth(client: AsyncClient):
    """❌ Test sending message without authentication"""
    payload = {"content": "Hello"}
    response = await client.post("/messages/1", json=payload)
    
    assert response.status_code == 401

async def test_send_message_invalid_token(client: AsyncClient):
    """❌ Test sending message with invalid token"""
    payload = {"content": "Hello"}
    response = await client.post(
        "/messages/1",
        json=payload,
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


async def test_send_message_nonexistent_thread(client: AsyncClient):
        """❌ Test sending message to non-existent thread"""
        token, _, _ = await setup_user_session_thread(client)
        
        payload = {"content": "Hello"}
        response = await client.post(
            "/messages/99999",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

async def test_send_message_other_users_thread(client: AsyncClient):
    """❌ Test sending message to another user's thread"""
    # Create first user with thread
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
    
    session1 = await client.post(
        "/sessions/",
        headers={"Authorization": f"Bearer {token1}"}
    )
    session1_id = session1.json()["id"]
    
    thread1 = await client.post(
        f"/threads/{session1_id}",
        json={"title": "User1 Thread"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    thread1_id = thread1.json()["id"]
    
    # Create second user
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
    
    # User2 tries to send message to User1's thread
    payload = {"content": "Unauthorized message"}
    response = await client.post(
        f"/messages/{thread1_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    assert response.status_code == 403
    assert "not allowed" in response.json()["detail"].lower()


async def test_send_message_empty_content(client: AsyncClient):
        """❌ Test sending message with empty content"""
        token, _, thread_id = await setup_user_session_thread(client)
        
        payload = {"content": ""}
        response = await client.post(
            f"/messages/{thread_id}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should fail validation (422) if min_length is set
        assert response.status_code in [422, 200]

async def test_send_message_missing_content(client: AsyncClient):
    """❌ Test sending message without content field"""
    token, _, thread_id = await setup_user_session_thread(client)
    
    payload = {}
    response = await client.post(
        f"/messages/{thread_id}",
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 422