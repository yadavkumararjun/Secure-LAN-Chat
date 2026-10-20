import uuid
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.database import init_db
from app.services.rate_limiter import chat_rate_limiter
from app.websocket.manager import ws_manager


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def _register_user(client: TestClient, prefix: str = "user"):
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    res = client.post(
        "/api/auth/register",
        json={"username": username, "password": "Password123!", "display_name": f"Name {username}"},
    )
    assert res.status_code == 201
    data = res.json()
    chat_rate_limiter.reset(data["id"])
    return data


def _receive_event(ws, expected_event: str):
    """Drain frames until the expected event is encountered."""
    for _ in range(10):  # At most 10 frames
        frame = ws.receive_json()
        if frame.get("event") == expected_event:
            return frame
    raise TimeoutError(f"Event '{expected_event}' was not received within frame window.")


def test_broadcast_messaging_and_delivery():
    """Verify broadcast messaging: all connected peers receive broadcast message with delivery confirmation."""
    with TestClient(app) as client_a, TestClient(app) as client_b:
        user_a = _register_user(client_a, "broad_a")
        user_b = _register_user(client_b, "broad_b")

        with client_a.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_a, \
             client_b.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_b:

            # Verify handshake
            auth_a = _receive_event(ws_a, "AUTH_SUCCESS")
            assert auth_a["data"]["user_id"] == user_a["id"]

            auth_b = _receive_event(ws_b, "AUTH_SUCCESS")
            assert auth_b["data"]["user_id"] == user_b["id"]

            # Client A sends a broadcast message to '#general-lan'
            client_msg_id = f"cmsg_{uuid.uuid4().hex[:8]}"
            ws_a.send_json({
                "event": "CHAT_MESSAGE",
                "data": {
                    "conversation_id": "broadcast-general",
                    "content": "Hello to everyone on local LAN!",
                    "client_msg_id": client_msg_id,
                },
            })

            # 1. Sender A must receive delivery confirmation (MESSAGE_ACK)
            ack = _receive_event(ws_a, "MESSAGE_ACK")
            assert ack["data"]["client_msg_id"] == client_msg_id
            assert ack["data"]["status"] == "sent"
            assert "message_id" in ack["data"]

            # 2. Both Sender A and Peer B receive NEW_MESSAGE event
            new_msg_a = _receive_event(ws_a, "NEW_MESSAGE")
            assert new_msg_a["data"]["message"]["content"] == "Hello to everyone on local LAN!"
            assert new_msg_a["data"]["message"]["sender"]["id"] == user_a["id"]

            new_msg_b = _receive_event(ws_b, "NEW_MESSAGE")
            assert new_msg_b["data"]["message"]["content"] == "Hello to everyone on local LAN!"
            assert new_msg_b["data"]["message"]["sender"]["id"] == user_a["id"]

        # 3. Message is persisted in SQLite and can be retrieved via REST
        res = client_b.get("/api/conversations/broadcast-general/messages")
        assert res.status_code == 200
        history = res.json()
        assert any(m["content"] == "Hello to everyone on local LAN!" for m in history["messages"])


def test_private_message_isolation():
    """
    Verify strict 1-to-1 message isolation:
    - User A and User B exchange private messages.
    - Unrelated User C does NOT receive WebSocket events and is 403 Forbidden from reading history.
    """
    with TestClient(app) as client_a, TestClient(app) as client_b, TestClient(app) as client_c:
        user_a = _register_user(client_a, "alice")
        user_b = _register_user(client_b, "bob")
        user_c = _register_user(client_c, "eve_snooper")

        # Create direct conversation between Alice and Bob
        dm_res = client_a.post("/api/conversations/direct", json={"recipient_id": user_b["id"]})
        assert dm_res.status_code == 200
        dm_id = dm_res.json()["id"]

        with client_a.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_a, \
             client_b.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_b, \
             client_c.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_c:

            # Verify handshakes
            assert _receive_event(ws_a, "AUTH_SUCCESS")["data"]["user_id"] == user_a["id"]
            assert _receive_event(ws_b, "AUTH_SUCCESS")["data"]["user_id"] == user_b["id"]
            assert _receive_event(ws_c, "AUTH_SUCCESS")["data"]["user_id"] == user_c["id"]

            # Alice sends a private message to Bob
            secret_text = f"Top-secret private note {uuid.uuid4().hex[:6]}"
            client_msg_id = f"cmsg_{uuid.uuid4().hex[:8]}"

            ws_a.send_json({
                "event": "CHAT_MESSAGE",
                "data": {
                    "conversation_id": dm_id,
                    "content": secret_text,
                    "client_msg_id": client_msg_id,
                },
            })

            # 1. Alice receives MESSAGE_ACK
            ack = _receive_event(ws_a, "MESSAGE_ACK")
            assert ack["data"]["client_msg_id"] == client_msg_id

            # 2. Alice receives NEW_MESSAGE
            alice_event = _receive_event(ws_a, "NEW_MESSAGE")
            assert alice_event["data"]["message"]["content"] == secret_text

            # 3. Bob receives NEW_MESSAGE
            bob_event = _receive_event(ws_b, "NEW_MESSAGE")
            assert bob_event["data"]["message"]["content"] == secret_text

            # 4. Eve sends ping to check her inbox
            ws_c.send_json({"type": "ping"})
            eve_reply = ws_c.receive_json()
            # If there was a presence event, drain it and get the pong
            if eve_reply.get("type") != "pong":
                eve_reply = ws_c.receive_json()
            assert eve_reply["type"] == "pong"

        # 5. Eve attempts to read Alice and Bob's private conversation history via REST
        eve_get = client_c.get(f"/api/conversations/{dm_id}/messages")
        assert eve_get.status_code == 403
        assert "Access forbidden" in eve_get.json()["error"]["message"]

        # 6. Eve attempts to send a message to Alice and Bob's DM
        eve_post = client_c.post(
            f"/api/conversations/{dm_id}/messages",
            json={"content": "Eve intruding"},
        )
        assert eve_post.status_code == 403


def test_message_persistence_and_pagination():
    """Verify message persistence in SQLite and chronological pagination."""
    with TestClient(app) as client:
        user = _register_user(client, "pager")
        conv_id = "broadcast-general"

        # Seed 12 distinct messages (reset rate limiter before each to avoid false rate limiting in test)
        for i in range(12):
            chat_rate_limiter.reset(user["id"])
            res = client.post(
                f"/api/conversations/{conv_id}/messages",
                json={"content": f"Numbered test message {i:02d}", "client_msg_id": f"page_{i}_{uuid.uuid4().hex[:4]}"},
            )
            assert res.status_code == 201

        # Page 1: limit 5, offset 0 (most recent 5 messages)
        p1 = client.get(f"/api/conversations/{conv_id}/messages?limit=5&offset=0").json()
        assert len(p1["messages"]) == 5
        assert p1["has_more"] is True
        assert p1["total"] >= 12

        # Page 2: limit 5, offset 5 (preceding 5 messages)
        p2 = client.get(f"/api/conversations/{conv_id}/messages?limit=5&offset=5").json()
        assert len(p2["messages"]) == 5

        # Verify no duplicate messages between consecutive pages
        p1_ids = {m["id"] for m in p1["messages"]}
        p2_ids = {m["id"] for m in p2["messages"]}
        assert len(p1_ids.intersection(p2_ids)) == 0


def test_message_deduplication_on_reconnect():
    """Verify that re-submitting an identical client_msg_id is idempotent and avoids duplicate DB rows."""
    with TestClient(app) as client:
        user = _register_user(client, "dedup")
        fixed_client_msg_id = f"idempotent_{uuid.uuid4().hex}"

        # First submission
        res1 = client.post(
            "/api/conversations/broadcast-general/messages",
            json={"content": "Idempotent packet transmission", "client_msg_id": fixed_client_msg_id},
        )
        assert res1.status_code == 201
        first_id = res1.json()["id"]

        # Second submission (simulating reconnect retry)
        res2 = client.post(
            "/api/conversations/broadcast-general/messages",
            json={"content": "Idempotent packet transmission", "client_msg_id": fixed_client_msg_id},
        )
        # Should return the existing message with identical ID
        assert res2.status_code == 201
        assert res2.json()["id"] == first_id

        # Verify database has only 1 entry with this client_msg_id
        hist = client.get("/api/conversations/broadcast-general/messages?limit=50").json()
        matching = [m for m in hist["messages"] if m.get("client_msg_id") == fixed_client_msg_id]
        assert len(matching) == 1


def test_rate_limiting():
    """Verify that excessive rapid message bursts are rate-limited with HTTP 429 / RATE_LIMITED."""
    with TestClient(app) as client:
        user = _register_user(client, "speedy")
        chat_rate_limiter.reset(user["id"])

        successful = 0
        rate_limited = 0

        # Attempt to post 15 messages in rapid succession
        for i in range(15):
            res = client.post(
                "/api/conversations/broadcast-general/messages",
                json={"content": f"Rapid burst packet #{i}"},
            )
            if res.status_code == 201:
                successful += 1
            elif res.status_code == 429:
                rate_limited += 1

        assert successful == 10
        assert rate_limited == 5


def test_malformed_and_oversized_payloads():
    """Verify WebSocket handles invalid frames, oversized content, and malformed JSON safely."""
    with TestClient(app) as client:
        user = _register_user(client, "fuzzer")

        with client.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws:
            # Verify handshake
            assert _receive_event(ws, "AUTH_SUCCESS")["data"]["user_id"] == user["id"]

            # 1. Non-JSON string
            ws.send_text("NOT_VALID_JSON{{{")
            err1 = _receive_event(ws, "ERROR")
            assert err1["data"]["code"] == "INVALID_JSON"

            # 2. Empty content
            ws.send_json({
                "event": "CHAT_MESSAGE",
                "data": {"conversation_id": "broadcast-general", "content": "   "},
            })
            err2 = _receive_event(ws, "ERROR")
            assert err2["data"]["code"] == "INVALID_PAYLOAD"

            # 3. Oversized content (> 2000 characters)
            ws.send_json({
                "event": "CHAT_MESSAGE",
                "data": {"conversation_id": "broadcast-general", "content": "A" * 2500},
            })
            err3 = _receive_event(ws, "ERROR")
            assert err3["data"]["code"] == "INVALID_PAYLOAD"


def test_disconnected_recipient_persistence():
    """Verify that private messages sent while recipient is offline are persisted and accessible on next login."""
    with TestClient(app) as client_a, TestClient(app) as client_b:
        user_a = _register_user(client_a, "sender_a")
        user_b = _register_user(client_b, "offline_b")

        # User B does NOT connect WebSocket (offline)
        assert not ws_manager.is_user_online(user_b["id"])

        # User A sends a private message to User B
        dm_res = client_a.post("/api/conversations/direct", json={"recipient_id": user_b["id"]})
        assert dm_res.status_code == 200
        dm_id = dm_res.json()["id"]

        offline_content = f"Offline stored message {uuid.uuid4().hex[:6]}"
        send_res = client_a.post(
            f"/api/conversations/{dm_id}/messages",
            json={"content": offline_content},
        )
        assert send_res.status_code == 201

        # User B logs in and fetches conversation history
        history = client_b.get(f"/api/conversations/{dm_id}/messages").json()
        assert any(m["content"] == offline_content for m in history["messages"])
