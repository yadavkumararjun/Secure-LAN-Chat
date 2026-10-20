import uuid
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.database import init_db
from app.websocket.manager import ws_manager


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_websocket_presence_and_cleanup():
    """Verify WebSocket authentication via cookie and presence cleanup on disconnect."""
    with TestClient(app) as client:
        username = f"presence_{uuid.uuid4().hex[:8]}"
        reg_res = client.post(
            "/api/auth/register",
            json={"username": username, "password": "Password123!", "display_name": "Presence Test 1"},
        )
        assert reg_res.status_code == 201
        user_id = reg_res.json()["id"]

        # User should start offline before connecting socket
        assert not ws_manager.is_user_online(user_id)

        # Connect WebSocket passing authenticated session cookies and allowed LAN origin
        with client.websocket_connect(
            "/ws/presence",
            headers={"Origin": "http://localhost:5173"},
        ) as websocket:
            # 1. Receive initial AUTH_SUCCESS frame
            data = websocket.receive_json()
            assert data["event"] == "AUTH_SUCCESS"
            assert data["data"]["user_id"] == user_id

            # 2. Receive PRESENCE_CHANGE broadcast frame
            presence_data = websocket.receive_json()
            assert presence_data["event"] == "PRESENCE_CHANGE"
            assert presence_data["data"]["status"] == "online"

            # 3. Verify user is now reported as online
            assert ws_manager.is_user_online(user_id)

            # 4. Test bidirectional ping-pong heartbeat
            websocket.send_json({"type": "ping"})
            pong_data = websocket.receive_json()
            assert pong_data["type"] == "pong"

            # 4. Check user list reflects is_online = True
            users_res = client.get("/api/users")
            assert users_res.status_code == 200
            user_item = next(u for u in users_res.json() if u["id"] == user_id)
            assert user_item["is_online"] is True

        # 5. Socket context has exited (disconnect completed)
        # Verify presence cleanup: user transitions to offline
        assert not ws_manager.is_user_online(user_id)

        # 6. Verify user list now reflects is_online = False
        users_res_after = client.get("/api/users")
        user_item_after = next(u for u in users_res_after.json() if u["id"] == user_id)
        assert user_item_after["is_online"] is False


def test_websocket_unauthenticated_rejected():
    """Verify WebSocket rejects connection when session cookie is missing."""
    with TestClient(app) as client:
        # Do not log in; no cookies
        client.cookies.clear()
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                "/ws/presence",
                headers={"Origin": "http://localhost:5173"},
            ):
                pass
        # Should be closed with policy violation code
        assert exc.value.code == 1008


def test_websocket_forbidden_origin_rejected():
    """Verify WebSocket rejects connection from unauthorized origin."""
    with TestClient(app) as client:
        # Register to obtain valid session cookie
        client.post(
            "/api/auth/register",
            json={"username": f"origin_{uuid.uuid4().hex[:8]}", "password": "Password123!"},
        )

        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(
                "/ws/presence",
                headers={"Origin": "http://malicious-external-site.com"},
            ):
                pass
        assert exc.value.code == 1008
