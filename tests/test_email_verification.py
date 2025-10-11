# import pytest
# from httpx import AsyncClient
# from unittest.mock import patch, MagicMock
# from app.config import settings


# @pytest.mark.asyncio
# class TestEmailVerification:
#     """Test suite for email verification functionality"""

#     # ========================================================================
#     # REGISTRATION WITH EMAIL VERIFICATION
#     # ========================================================================

#     @patch('app.routers.auth.EmailService.send_verification_email')
#     @patch('app.routers.auth.EmailService.generate_verification_token')
#     async def test_register_sends_verification_email(
#         self, 
#         mock_generate_token, 
#         mock_send_email,
#         client: AsyncClient
#     ):
#         """✅ Test that registration sends verification email"""
#         mock_generate_token.return_value = "test_token_123"
#         mock_send_email.return_value = None
        
#         payload = {
#             "username": "emailuser",
#             "email": "emailuser@example.com",
#             "password": "password123"
#         }
        
#         response = await client.post("/auth/register", json=payload)
        
#         assert response.status_code == 201
#         data = response.json()
#         assert data["is_verified"] is False
        
#         # Verify email sending was attempted (if EMAIL_VERIFICATION_REQUIRED=True)
#         if settings.EMAIL_VERIFICATION_REQUIRED:
#             mock_generate_token.assert_called_once()
#             mock_send_email.assert_called_once()

#     @patch('app.routers.auth.EmailService.send_verification_email')
#     @patch('app.routers.auth.EmailService.generate_verification_token')
#     async def test_register_continues_if_email_fails(
#         self,
#         mock_generate_token,
#         mock_send_email,
#         client: AsyncClient
#     ):
#         """✅ Test that registration succeeds even if email fails"""
#         from app.services.email_service import EmailSendError
        
#         mock_generate_token.return_value = "test_token_123"
#         mock_send_email.side_effect = EmailSendError("SMTP error")
        
#         payload = {
#             "username": "emailfailuser",
#             "email": "emailfail@example.com",
#             "password": "password123"
#         }
        
#         response = await client.post("/auth/register", json=payload)
        
#         # Registration should still succeed
#         assert response.status_code == 201
#         assert response.json()["is_verified"] is False

#     # ========================================================================
#     # EMAIL VERIFICATION ENDPOINT
#     # ========================================================================

#     async def test_verify_email_success(self, client: AsyncClient, db_session):
#         """✅ Test successful email verification"""
#         from app.services.user_service import UserService
#         from app.services.email_service import EmailService
#         from app.schemas.schemas import UserCreate
        
#         # Create user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="verifyuser",
#             email="verify@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
        
#         # Generate token
#         email_svc = EmailService(db_session)
#         token = await email_svc.generate_verification_token(user.id)
        
#         # Verify email
#         response = await client.get(f"/auth/verify-email?token={token}")
        
#         assert response.status_code == 200
#         data = response.json()
#         assert data["message"] == "Email verified successfully"
#         assert data["email"] == "verify@example.com"

#     async def test_verify_email_invalid_token(self, client: AsyncClient):
#         """❌ Test verification with invalid token"""
#         response = await client.get("/auth/verify-email?token=invalid_token_123")
        
#         assert response.status_code == 400
#         assert "invalid" in response.json()["detail"].lower()

#     async def test_verify_email_expired_token(self, client: AsyncClient, db_session):
#         """❌ Test verification with expired token"""
#         from app.services.user_service import UserService
#         from app.services.email_service import EmailService
#         from app.schemas.schemas import UserCreate
#         from app.models.email_verification import EmailVerificationToken
#         from datetime import datetime, timedelta, timezone
        
#         # Create user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="expireduser",
#             email="expired@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
        
#         # Create expired token manually
#         import secrets
#         token = secrets.token_urlsafe(32)
#         expired_token = EmailVerificationToken(
#             user_id=user.id,
#             token=token,
#             expires_at=datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
#         )
#         db_session.add(expired_token)
#         await db_session.commit()
        
#         # Try to verify
#         response = await client.get(f"/auth/verify-email?token={token}")
        
#         assert response.status_code == 400
#         assert "expired" in response.json()["detail"].lower()

#     async def test_verify_email_already_used_token(self, client: AsyncClient, db_session):
#         """❌ Test verification with already used token"""
#         from app.services.user_service import UserService
#         from app.services.email_service import EmailService
#         from app.schemas.schemas import UserCreate
        
#         # Create user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="usedtokenuser",
#             email="usedtoken@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
        
#         # Generate token
#         email_svc = EmailService(db_session)
#         token = await email_svc.generate_verification_token(user.id)
        
#         # Verify first time (success)
#         response1 = await client.get(f"/auth/verify-email?token={token}")
#         assert response1.status_code == 200
        
#         # Try to verify again (should fail)
#         response2 = await client.get(f"/auth/verify-email?token={token}")
#         assert response2.status_code == 400
#         assert "used" in response2.json()["detail"].lower()

#     async def test_verify_email_missing_token(self, client: AsyncClient):
#         """❌ Test verification without token parameter"""
#         response = await client.get("/auth/verify-email")
        
#         assert response.status_code == 422  # Validation error

#     # ========================================================================
#     # RESEND VERIFICATION EMAIL
#     # ========================================================================

#     @patch('app.services.email_service.EmailService.send_verification_email')
#     async def test_resend_verification_email_success(
#         self,
#         mock_send_email,
#         client: AsyncClient,
#         db_session
#     ):
#         """✅ Test resending verification email"""
#         from app.services.user_service import UserService
#         from app.schemas.schemas import UserCreate
        
#         mock_send_email.return_value = None
        
#         # Create unverified user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="resenduser",
#             email="resend@example.com",
#             password="password123"
#         )
#         await user_svc.register_user(user_data)
        
#         # Resend verification
#         response = await client.post(
#             "/auth/resend-verification",
#             json={"email": "resend@example.com"}
#         )
        
#         assert response.status_code == 200
#         data = response.json()
#         assert "sent successfully" in data["message"].lower()
#         mock_send_email.assert_called_once()

#     async def test_resend_verification_already_verified(
#         self,
#         client: AsyncClient,
#         db_session
#     ):
#         """❌ Test resending to already verified user"""
#         from app.services.user_service import UserService
#         from app.services.email_service import EmailService
#         from app.schemas.schemas import UserCreate
        
#         # Create and verify user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="alreadyverified",
#             email="alreadyverified@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
        
#         # Verify user
#         email_svc = EmailService(db_session)
#         token = await email_svc.generate_verification_token(user.id)
#         await email_svc.verify_email_token(token)
        
#         # Try to resend
#         response = await client.post(
#             "/auth/resend-verification",
#             json={"email": "alreadyverified@example.com"}
#         )
        
#         assert response.status_code == 400
#         assert "already verified" in response.json()["detail"].lower()

#     async def test_resend_verification_nonexistent_email(self, client: AsyncClient):
#         """✅ Test resending to non-existent email (should not reveal)"""
#         response = await client.post(
#             "/auth/resend-verification",
#             json={"email": "nonexistent@example.com"}
#         )
        
#         # Should return success to not reveal if email exists
#         assert response.status_code == 200
#         assert "sent" in response.json()["message"].lower()

#     async def test_resend_verification_missing_email(self, client: AsyncClient):
#         """❌ Test resending without email"""
#         response = await client.post("/auth/resend-verification", json={})
        
#         assert response.status_code == 422  # Validation error

#     # ========================================================================
#     # LOGIN WITH VERIFICATION CHECK
#     # ========================================================================

#     async def test_login_unverified_user_when_required(
#         self,
#         client: AsyncClient,
#         db_session
#     ):
#         """❌ Test login fails for unverified user when verification required"""
#         from app.services.user_service import UserService
#         from app.schemas.schemas import UserCreate
        
#         # Create unverified user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="unverifiedlogin",
#             email="unverifiedlogin@example.com",
#             password="password123"
#         )
#         await user_svc.register_user(user_data)
        
#         # Try to login
#         response = await client.post(
#             "/auth/login",
#             data={"username": "unverifiedlogin", "password": "password123"}
#         )
        
#         if settings.EMAIL_VERIFICATION_REQUIRED:
#             assert response.status_code == 401
#             assert "not verified" in response.json()["detail"].lower()
#         else:
#             # If verification not required, login should succeed
#             assert response.status_code == 200

#     async def test_login_verified_user_success(
#         self,
#         client: AsyncClient,
#         db_session
#     ):
#         """✅ Test login succeeds for verified user"""
#         from app.services.user_service import UserService
#         from app.services.email_service import EmailService
#         from app.schemas.schemas import UserCreate
        
#         # Create user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="verifiedlogin",
#             email="verifiedlogin@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
        
#         # Verify user
#         email_svc = EmailService(db_session)
#         token = await email_svc.generate_verification_token(user.id)
#         await email_svc.verify_email_token(token)
        
#         # Login
#         response = await client.post(
#             "/auth/login",
#             data={"username": "verifiedlogin", "password": "password123"}
#         )
        
#         assert response.status_code == 200
#         assert "access_token" in response.json()

#     # ========================================================================
#     # USER INFO INCLUDES VERIFICATION STATUS
#     # ========================================================================

#     async def test_user_info_includes_verification_status(
#         self,
#         client: AsyncClient,
#         db_session
#     ):
#         """✅ Test that user info includes is_verified field"""
#         from app.services.user_service import UserService
#         from app.schemas.schemas import UserCreate
        
#         # Create user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="statususer",
#             email="status@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
        
#         # Register returns user info
#         payload = {
#             "username": "statuscheck",
#             "email": "statuscheck@example.com",
#             "password": "password123"
#         }
#         response = await client.post("/auth/register", json=payload)
        
#         assert response.status_code == 201
#         data = response.json()
#         assert "is_verified" in data
#         assert data["is_verified"] is False

#     # ========================================================================
#     # INTEGRATION TESTS
#     # ========================================================================

#     async def test_complete_verification_flow(
#         self,
#         client: AsyncClient,
#         db_session
#     ):
#         """✅ Test complete verification flow"""
#         from app.services.user_service import UserService
#         from app.services.email_service import EmailService
#         from app.schemas.schemas import UserCreate
        
#         # Step 1: Register user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="completeflow",
#             email="completeflow@example.com",
#             password="password123"
#         )
#         user = await user_svc.register_user(user_data)
#         assert user.is_verified is False
        
#         # Step 2: Generate verification token
#         email_svc = EmailService(db_session)
#         token = await email_svc.generate_verification_token(user.id)
        
#         # Step 3: Verify email
#         verify_response = await client.get(f"/auth/verify-email?token={token}")
#         assert verify_response.status_code == 200
        
#         # Step 4: Login (should work now if verification required)
#         login_response = await client.post(
#             "/auth/login",
#             data={"username": "completeflow", "password": "password123"}
#         )
#         assert login_response.status_code == 200

#     @patch('app.services.email_service.EmailService.send_verification_email')
#     async def test_multiple_resend_requests(
#         self,
#         mock_send_email,
#         client: AsyncClient,
#         db_session
#     ):
#         """✅ Test multiple resend requests"""
#         from app.services.user_service import UserService
#         from app.schemas.schemas import UserCreate
        
#         mock_send_email.return_value = None
        
#         # Create user
#         user_svc = UserService(db_session)
#         user_data = UserCreate(
#             username="multiresend",
#             email="multiresend@example.com",
#             password="password123"
#         )
#         await user_svc.register_user(user_data)
        
#         # Resend multiple times
#         for i in range(3):
#             response = await client.post(
#                 "/auth/resend-verification",
#                 json={"email": "multiresend@example.com"}
#             )
#             assert response.status_code == 200
        
#         # Should have been called 3 times
#         assert mock_send_email.call_count == 3