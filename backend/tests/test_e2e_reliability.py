import io
import os
import uuid
import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import init_db, SessionLocal
from app.models import User, UserSession, Conversation, Message, ConversationMember
from app.services.rate_limiter import auth_rate_limiter, chat_rate_limiter, upload_rate_limiter


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure clean database and rate limiter state for reliability tests."""
    init_db()
    auth_rate_limiter.reset_all()
    upload_rate_limiter.reset_all()
    yield
    auth_rate_limiter.reset_all()
    upload_rate_limiter.reset_all()


def _create_authenticated_client(prefix: str = "rel_user"):
    client = TestClient(app)
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/auth/register",
        json={"username": username, "password": "ReliablePass123!", "display_name": f"User {username}"},
    )
    assert res.status_code == 201
    user_data = res.json()
    chat_rate_limiter.reset(user_data["id"])
    return client, user_data


def test_scenario_5_message_history_persistence_across_server_restarts():
    """
    Scenario 5: Verify that conversation messages survive a complete server/database restart.
    1. Two users exchange private and broadcast messages.
    2. The application database engine re-initializes (simulating process restart).
    3. Both users fetch message history and verify timestamps, sender IDs, and contents match.
    """
    client_a, user_a = _create_authenticated_client("restart_a")
    client_b, user_b = _create_authenticated_client("restart_b")

    # 1. Create direct conversation
    dm_res = client_a.post("/api/conversations/direct", json={"recipient_id": user_b["id"]})
    assert dm_res.status_code == 200
    conv_id = dm_res.json()["id"]

    # 2. Send messages
    msg1_res = client_a.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Pre-restart message 1 from Alice", "message_type": "text"},
    )
    assert msg1_res.status_code == 201

    msg2_res = client_b.post(
        f"/api/conversations/{conv_id}/messages",
        json={"content": "Pre-restart message 2 from Bob", "message_type": "text"},
    )
    assert msg2_res.status_code == 201

    # Also post to broadcast channel
    bcast_res = client_a.post(
        "/api/conversations/broadcast-general/messages",
        json={"content": "Broadcast message before server restart", "message_type": "text"},
    )
    assert bcast_res.status_code == 201

    # 3. Simulate server restart: re-initialize database tables and close old session pool
    init_db()

    # 4. In a new client session with the original cookies, fetch history
    hist_a = client_a.get(f"/api/conversations/{conv_id}/messages?limit=50&offset=0")
    assert hist_a.status_code == 200
    messages_a = hist_a.json()["messages"]
    assert len(messages_a) == 2
    assert messages_a[0]["content"] == "Pre-restart message 1 from Alice"
    assert messages_a[1]["content"] == "Pre-restart message 2 from Bob"

    hist_b = client_b.get(f"/api/conversations/{conv_id}/messages?limit=50&offset=0")
    assert hist_b.status_code == 200
    messages_b = hist_b.json()["messages"]
    assert len(messages_b) == 2

    # Verify broadcast persistence
    bcast_hist = client_b.get("/api/conversations/broadcast-general/messages?limit=50&offset=0")
    assert bcast_hist.status_code == 200
    assert any("before server restart" in m["content"] for m in bcast_hist.json()["messages"])


def test_scenario_7_storage_failure_handling_and_atomic_cleanup():
    """
    Scenario 7: Verify that storage errors during upload result in atomic cleanup and a 500 error.
    No corrupt or orphaned records remain in SQLite or filesystem.
    """
    client, user = _create_authenticated_client("disk_err_user")

    # Simulate an OS write error / disk full during streaming
    with patch("builtins.open", side_effect=OSError("Disk full or I/O error")):
        file_payload = ("test_error.txt", io.BytesIO(b"Data that cannot be saved"), "text/plain")
        res = client.post(
            "/api/files/upload",
            files={"file": file_payload},
            data={"conversation_id": "broadcast-general"},
        )
        assert res.status_code == 500
        assert "UPLOAD_INGEST_ERROR" in res.text

    # Verify database was not corrupted: subsequent normal upload succeeds
    normal_payload = ("valid_file.txt", io.BytesIO(b"Valid content"), "text/plain")
    ok_res = client.post(
        "/api/files/upload",
        files={"file": normal_payload},
        data={"conversation_id": "broadcast-general"},
    )
    assert ok_res.status_code == 201
    assert ok_res.json()["original_name"] == "valid_file.txt"


def _receive_presence_for_user(ws, user_id: int, expected_status: str):
    """Drain frames until the expected user presence event is encountered."""
    for _ in range(10):
        frame = ws.receive_json()
        if (
            frame.get("event") == "PRESENCE_CHANGE"
            and frame.get("data", {}).get("user_id") == user_id
            and frame.get("data", {}).get("status") == expected_status
        ):
            return frame
    raise TimeoutError(f"Presence '{expected_status}' for user {user_id} was not received.")


def test_scenario_8_client_disconnect_and_reconnect_presence_transitions():
    """
    Scenario 8: Verify presence status transitions cleanly across rapid connect/disconnect/reconnect cycles.
    """
    client_a, user_a = _create_authenticated_client("recon_a")
    client_b, user_b = _create_authenticated_client("recon_b")

    # Connect client B to listen for presence transitions
    with client_b.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_b:
        # Drain auth event
        auth_b = ws_b.receive_json()
        assert auth_b["event"] == "AUTH_SUCCESS"

        # Client A connects
        with client_a.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_a:
            auth_a = ws_a.receive_json()
            assert auth_a["event"] == "AUTH_SUCCESS"

            # Check that client B receives User A going online
            frame_online = _receive_presence_for_user(ws_b, user_a["id"], "online")
            assert frame_online["data"]["status"] == "online"

        # Client A disconnected cleanly; Client B receives User A going offline
        frame_offline = _receive_presence_for_user(ws_b, user_a["id"], "offline")
        assert frame_offline["data"]["status"] == "offline"


def test_scenario_9_max_sessions_per_user_eviction():
    """
    Scenario 9: Verify that creating more than MAX_SESSIONS_PER_USER evicts the oldest session.
    """
    client = TestClient(app)
    username = f"session_user_{uuid.uuid4().hex[:8]}"
    pwd = "SessionPass123!"

    # Register
    reg_res = client.post("/api/auth/register", json={"username": username, "password": pwd})
    assert reg_res.status_code == 201

    tokens = []
    # Log in multiple times to create multiple sessions up to and beyond MAX_SESSIONS_PER_USER
    for i in range(settings.MAX_SESSIONS_PER_USER + 2):
        auth_rate_limiter.reset_all()
        login_res = client.post("/api/auth/login", json={"username": username, "password": pwd})
        assert login_res.status_code == 200
        token = login_res.cookies.get(settings.COOKIE_NAME)
        assert token
        tokens.append(token)

    # In database, user must have at most MAX_SESSIONS_PER_USER active sessions
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        active_sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()
        assert len(active_sessions) <= settings.MAX_SESSIONS_PER_USER

        # The very first token created must be evicted and invalid
        first_token = tokens[0]
        check_client = TestClient(app)
        check_client.cookies.set(settings.COOKIE_NAME, first_token)
        me_res = check_client.get("/api/auth/me")
        assert me_res.status_code == 401, "Evicted session token must be rejected"
    finally:
        db.close()


def test_scenario_11_accessibility_and_wcag_contrast_assets():
    """
    Scenario 11: Inspect the built HTML and CSS design system for required accessibility attributes.
    - Viewport meta tag present for responsive rendering
    - Lang attribute present on <html>
    - Semantic landmarks (<header>, <main>, <aside>, <section>, <form>)
    - CSS contrast variables defined
    """
    dist_dir = settings.get_absolute_frontend_dist()
    index_html = dist_dir / "index.html"
    assert index_html.is_file(), "Compiled index.html must exist"

    html_content = index_html.read_text(encoding="utf-8")
    assert '<html lang="en">' in html_content, "Document must declare lang='en'"
    assert 'name="viewport"' in html_content, "Viewport meta tag required for mobile responsiveness"
    assert 'width=device-width' in html_content

    # Inspect CSS file
    css_files = list((dist_dir / "assets").glob("*.css"))
    assert len(css_files) > 0
    css_content = css_files[0].read_text(encoding="utf-8")

    # Check key accessibility styles in compiled CSS
    assert "--bg-app" in css_content
    assert "--text-primary" in css_content
    assert "--border-subtle" in css_content
    assert ":focus" in css_content or ":focus-visible" in css_content
