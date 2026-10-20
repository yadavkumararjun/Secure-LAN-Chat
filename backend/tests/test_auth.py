import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models import User, UserSession
from app.security.hashing import verify_password


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database schema is fresh and ready before each test."""
    init_db()


def test_user_registration_success():
    """Verify registration creates user with Argon2id hash and sets HTTP-only cookie."""
    with TestClient(app) as client:
        username = f"user_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": "ValidPassword123!",
                "display_name": "New LAN User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == username
        assert data["display_name"] == "New LAN User"
        assert "password" not in data
        assert "password_hash" not in data

        # Verify HTTP-only session cookie is attached
        assert "session_id" in response.cookies

        # Verify database record: Password is never plaintext
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.username == username).first()
            assert db_user is not None
            assert db_user.password_hash != "ValidPassword123!"
            assert db_user.password_hash.startswith("$argon2id$")
            assert verify_password("ValidPassword123!", db_user.password_hash)
        finally:
            db.close()


def test_registration_duplicate_username():
    """Verify duplicate username registration is rejected with 409 Conflict."""
    with TestClient(app) as client:
        dup_name = f"dup_{uuid.uuid4().hex[:8]}"
        payload = {
            "username": dup_name,
            "password": "Password123!",
            "display_name": "Duplicate Test",
        }
        # First registration
        res1 = client.post("/api/auth/register", json=payload)
        assert res1.status_code == 201

        # Second registration with same username
        res2 = client.post("/api/auth/register", json=payload)
        assert res2.status_code == 409
        err = res2.json()
        assert err["error"]["code"] == "CONFLICT"
        assert "already taken" in err["error"]["message"].lower()


def test_registration_validation_rules():
    """Verify username and password validation constraints."""
    with TestClient(app) as client:
        # Username too short (< 3 chars)
        res1 = client.post(
            "/api/auth/register",
            json={"username": "ab", "password": "Password123!"},
        )
        assert res1.status_code == 422

        # Username with invalid special characters
        res2 = client.post(
            "/api/auth/register",
            json={"username": "user!@#$%", "password": "Password123!"},
        )
        assert res2.status_code == 422

        # Password too short (< 6 chars)
        res3 = client.post(
            "/api/auth/register",
            json={"username": "valid_user_short_pass", "password": "123"},
        )
        assert res3.status_code == 422


def test_login_success_and_logout():
    """Verify login with correct credentials and subsequent logout."""
    with TestClient(app) as client:
        username = f"login_{uuid.uuid4().hex[:8]}"
        password = "SecurePassword2026!"

        # Register
        reg_res = client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )
        assert reg_res.status_code == 201

        # Clear cookies to simulate fresh browser session
        client.cookies.clear()

        # Login
        login_res = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert login_res.status_code == 200
        assert "session_id" in login_res.cookies

        # Test authenticated /me
        me_res = client.get("/api/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["username"] == username

        # Logout
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # Verify /me is now unauthorized
        after_logout = client.get("/api/auth/me")
        assert after_logout.status_code == 401


def test_login_incorrect_password():
    """Verify login with wrong password returns 401 Unauthorized."""
    with TestClient(app) as client:
        username = f"wrong_{uuid.uuid4().hex[:8]}"
        client.post(
            "/api/auth/register",
            json={"username": username, "password": "CorrectPassword123"},
        )

        client.cookies.clear()
        res = client.post(
            "/api/auth/login",
            json={"username": username, "password": "WrongPassword999"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_unauthenticated_access():
    """Verify protected routes reject requests without a valid session cookie."""
    with TestClient(app) as client:
        # Access /me with no cookie
        res1 = client.get("/api/auth/me")
        assert res1.status_code == 401

        # Access /api/users with no cookie
        res2 = client.get("/api/users")
        assert res2.status_code == 401


def test_user_search_and_list():
    """Verify authenticated user search and list endpoint."""
    with TestClient(app) as client:
        alice_name = f"alice_{uuid.uuid4().hex[:6]}"
        bob_name = f"bob_{uuid.uuid4().hex[:6]}"

        # Register user A and log in
        client.post(
            "/api/auth/register",
            json={"username": alice_name, "password": "Password123!", "display_name": "Alice Wonder"},
        )

        # Register user B
        client.post(
            "/api/auth/register",
            json={"username": bob_name, "password": "Password123!", "display_name": "Bob Builder"},
        )

        # List all users
        res = client.get("/api/users")
        assert res.status_code == 200
        users = res.json()
        usernames = [u["username"] for u in users]
        assert alice_name in usernames
        assert bob_name in usernames

        # Search for alice
        search_res = client.get(f"/api/users?q={alice_name}")
        assert search_res.status_code == 200
        results = search_res.json()
        assert len(results) >= 1
        assert results[0]["username"] == alice_name
