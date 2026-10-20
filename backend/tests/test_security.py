import io
import uuid
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.config import settings
from app.services.rate_limiter import auth_rate_limiter, upload_rate_limiter


def _register_and_login(client: TestClient, prefix: str = "sec_user"):
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/auth/register",
        json={"username": username, "password": "Password123!", "display_name": f"Name {username}"},
    )
    assert res.status_code == 201
    return res.json()


def test_security_headers_present():
    """Verify that defense-in-depth security headers are attached to HTTP responses."""
    with TestClient(app) as client:
        res = client.get("/api/health")
        assert res.status_code == 200

        headers = res.headers
        assert headers.get("x-content-type-options") == "nosniff"
        assert headers.get("x-frame-options") == "DENY"
        assert headers.get("x-xss-protection") == "1; mode=block"
        assert "strict-origin-when-cross-origin" in headers.get("referrer-policy", "")
        assert "frame-ancestors 'none'" in headers.get("content-security-policy", "")
        assert "camera=()" in headers.get("permissions-policy", "")


def test_authentication_bypass_blocked():
    """Verify that unauthenticated requests to protected endpoints are blocked with 401 Unauthorized."""
    with TestClient(app) as anon_client:
        # 1. User profile
        r1 = anon_client.get("/api/auth/me")
        assert r1.status_code == 401
        assert r1.json()["error"]["code"] == "UNAUTHORIZED"

        # 2. Directory listing
        r2 = anon_client.get("/api/users")
        assert r2.status_code == 401

        # 3. Conversations list
        r3 = anon_client.get("/api/conversations")
        assert r3.status_code == 401

        # 4. Message history
        r4 = anon_client.get("/api/conversations/broadcast-general/messages")
        assert r4.status_code == 401

        # 5. File upload
        r5 = anon_client.post(
            "/api/files/upload",
            files={"file": ("test.txt", io.BytesIO(b"content"), "text/plain")},
            data={"conversation_id": "broadcast-general"},
        )
        assert r5.status_code == 401

        # 6. File download
        r6 = anon_client.get("/api/files/1/download")
        assert r6.status_code == 401


def test_login_brute_force_rate_limiting():
    """Verify that brute-force login attempts from the same IP are rate-limited with 429 Too Many Requests."""
    auth_rate_limiter.reset_all()

    with TestClient(app) as client:
        # Exhaust rate limit quota
        for _ in range(settings.RATE_LIMIT_AUTH_ATTEMPTS):
            res = client.post("/api/auth/login", json={"username": "nonexistent_user", "password": "WrongPassword!"})
            assert res.status_code == 401

        # Next request must be blocked by rate limiter
        blocked_res = client.post("/api/auth/login", json={"username": "nonexistent_user", "password": "WrongPassword!"})
        assert blocked_res.status_code == 429
        assert blocked_res.json()["error"]["code"] == "RATE_LIMITED"


def test_file_upload_rate_limiting():
    """Verify that spamming file uploads triggers 429 Too Many Requests rate limiting."""
    upload_rate_limiter.reset_all()

    with TestClient(app) as client:
        user = _register_and_login(client, "uploader")

        # Send uploads up to quota
        for i in range(settings.RATE_LIMIT_UPLOAD_FILES):
            res = client.post(
                "/api/files/upload",
                files={"file": (f"doc_{i}.txt", io.BytesIO(b"test data"), "text/plain")},
                data={"conversation_id": "broadcast-general"},
            )
            assert res.status_code == 201

        # Next upload should be rate limited
        blocked = client.post(
            "/api/files/upload",
            files={"file": ("blocked.txt", io.BytesIO(b"test data"), "text/plain")},
            data={"conversation_id": "broadcast-general"},
        )
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_websocket_unauthorized_origin_rejection():
    """Verify that WebSocket handshakes from unauthorized origins (CSWSH defense) are rejected."""
    with TestClient(app) as client:
        _register_and_login(client, "origin_user")
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/chat", headers={"Origin": "http://evil-malicious-site.com"}):
                pass
        assert exc_info.value.code == 1008  # Policy violation


def test_websocket_unauthenticated_rejection():
    """Verify that anonymous clients without session cookies cannot establish WebSocket connections."""
    with TestClient(app) as anon_client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with anon_client.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}):
                pass
        assert exc_info.value.code == 1008


def _receive_event(ws, expected_event: str):
    """Drain frames until the expected event is encountered."""
    for _ in range(10):
        frame = ws.receive_json()
        if frame.get("event") == expected_event:
            return frame
    raise TimeoutError(f"Event '{expected_event}' was not received within frame window.")


def test_websocket_oversized_payload_rejected():
    """Verify that sending a raw WebSocket frame exceeding MAX_WS_FRAME_SIZE_BYTES returns MESSAGE_TOO_LARGE."""
    with TestClient(app) as client:
        _register_and_login(client, "frame_user")
        with client.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws:
            # Drain handshake
            auth = _receive_event(ws, "AUTH_SUCCESS")
            assert auth["event"] == "AUTH_SUCCESS"

            # Create oversized text payload > 64 KB
            huge_content = "A" * (settings.MAX_WS_FRAME_SIZE_BYTES + 500)
            ws.send_text(huge_content)

            err = _receive_event(ws, "ERROR")
            assert err["event"] == "ERROR"
            assert err["data"]["code"] == "MESSAGE_TOO_LARGE"


def test_cross_user_private_chat_isolation():
    """Verify horizontal privilege separation: User C cannot read or post to User A and User B's private chat."""
    with TestClient(app) as client_a, TestClient(app) as client_b, TestClient(app) as client_c:
        user_a = _register_and_login(client_a, "alice")
        user_b = _register_and_login(client_b, "bob")
        user_c = _register_and_login(client_c, "charlie")

        # Alice creates private chat with Bob
        conv_res = client_a.post("/api/conversations/direct", json={"recipient_id": user_b["id"]})
        assert conv_res.status_code == 200
        conv_id = conv_res.json()["id"]

        # Alice sends private message
        msg_res = client_a.post(f"/api/conversations/{conv_id}/messages", json={"content": "Confidential meeting"})
        assert msg_res.status_code == 201

        # 1. Charlie attempts to read private messages -> 403 Forbidden
        read_res = client_c.get(f"/api/conversations/{conv_id}/messages")
        assert read_res.status_code == 403
        assert read_res.json()["error"]["code"] == "ACCESS_FORBIDDEN"

        # 2. Charlie attempts to post to private conversation -> 403 Forbidden
        post_res = client_c.post(f"/api/conversations/{conv_id}/messages", json={"content": "Intruder message"})
        assert post_res.status_code == 403
        assert post_res.json()["error"]["code"] == "ACCESS_FORBIDDEN"


def test_cross_user_private_file_download_isolation():
    """Verify that User C cannot download a private file or inspect its metadata."""
    with TestClient(app) as client_a, TestClient(app) as client_b, TestClient(app) as client_c:
        user_a = _register_and_login(client_a, "file_a")
        user_b = _register_and_login(client_b, "file_b")
        user_c = _register_and_login(client_c, "file_c")

        # Direct conversation between A and B
        conv_res = client_a.post("/api/conversations/direct", json={"recipient_id": user_b["id"]})
        conv_id = conv_res.json()["id"]

        # A uploads confidential file
        upload_res = client_a.post(
            "/api/files/upload",
            files={"file": ("secret_key.pem", io.BytesIO(b"PRIVATE_KEY_DATA"), "application/x-pem-file")},
            data={"conversation_id": conv_id},
        )
        assert upload_res.status_code == 201
        file_id = upload_res.json()["id"]

        # Outsider Charlie download -> 403
        dl_res = client_c.get(f"/api/files/{file_id}/download")
        assert dl_res.status_code == 403
        assert dl_res.json()["error"]["code"] == "ACCESS_FORBIDDEN"

        # Outsider Charlie metadata -> 403
        meta_res = client_c.get(f"/api/files/{file_id}")
        assert meta_res.status_code == 403


def test_invalid_conversation_id_format_rejection():
    """Verify that malformed or path-traversal conversation IDs are rejected with 400 Bad Request."""
    with TestClient(app) as client:
        _register_and_login(client, "valid_user")

        # 1. Path traversal attempt
        r1 = client.get("/api/conversations/..%2F..%2Fetc%2Fpasswd/messages")
        assert r1.status_code in (400, 404)

        # 2. Malicious chars
        r2 = client.get("/api/conversations/dm_1_2;DROP_TABLE/messages")
        assert r2.status_code == 400
        assert r2.json()["error"]["code"] == "INVALID_CONVERSATION_ID"


def test_logout_invalidates_session_token():
    """Verify that logging out revokes the session in SQLite and renders subsequent requests unauthorized."""
    with TestClient(app) as client:
        _register_and_login(client, "logout_user")

        # Verify currently authenticated
        me_res = client.get("/api/auth/me")
        assert me_res.status_code == 200

        # Sign out
        logout_res = client.post("/api/auth/logout")
        assert logout_res.status_code == 200

        # Verify session is destroyed
        me_after = client.get("/api/auth/me")
        assert me_after.status_code == 401
