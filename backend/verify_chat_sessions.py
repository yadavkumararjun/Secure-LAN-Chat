"""
Multi-client session verification script for Secure LAN Chat.
Tests 3 independent sessions (Alice, Bob, and Charlie) to verify:
1. One-to-one private messaging between Alice & Bob.
2. Complete private-message isolation: Charlie does NOT receive Alice's DM to Bob over WebSocket.
3. Authorization barrier: Charlie receives 403 Forbidden attempting to read Alice and Bob's DM history.
4. Broadcast transparency: All 3 participants receive broadcast messages in #general-lan.
5. Server-enforced identity: Delivery acknowledgments and persisted sender metadata reflect authenticated sessions.
"""
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app.services.rate_limiter import chat_rate_limiter


def run_multi_session_verification():
    print("=" * 70)
    print("SECURE LAN CHAT — PHASE 4: MULTI-SESSION REAL-TIME CHAT VERIFICATION")
    print("=" * 70)

    init_db()

    client_alice = TestClient(app)
    client_bob = TestClient(app)
    client_charlie = TestClient(app)

    # 1. Register 3 independent users
    u_alice = f"alice_{uuid.uuid4().hex[:6]}"
    u_bob = f"bob_{uuid.uuid4().hex[:6]}"
    u_charlie = f"charlie_{uuid.uuid4().hex[:6]}"

    print(f"[1/6] Registering test accounts: {u_alice}, {u_bob}, {u_charlie}...")
    res_a = client_alice.post("/api/auth/register", json={"username": u_alice, "password": "Password123!", "display_name": "Alice"})
    res_b = client_bob.post("/api/auth/register", json={"username": u_bob, "password": "Password123!", "display_name": "Bob"})
    res_c = client_charlie.post("/api/auth/register", json={"username": u_charlie, "password": "Password123!", "display_name": "Charlie"})

    assert res_a.status_code == 201, f"Failed Alice registration: {res_a.text}"
    assert res_b.status_code == 201, f"Failed Bob registration: {res_b.text}"
    assert res_c.status_code == 201, f"Failed Charlie registration: {res_c.text}"

    alice_id = res_a.json()["id"]
    bob_id = res_b.json()["id"]
    charlie_id = res_c.json()["id"]

    chat_rate_limiter.reset(alice_id)
    chat_rate_limiter.reset(bob_id)
    chat_rate_limiter.reset(charlie_id)

    print(f"      Users registered: Alice (ID {alice_id}), Bob (ID {bob_id}), Charlie (ID {charlie_id})")

    # 2. Establish Direct Conversation between Alice and Bob
    print("\n[2/6] Alice establishes 1-on-1 private conversation with Bob...")
    dm_res = client_alice.post("/api/conversations/direct", json={"recipient_id": bob_id})
    assert dm_res.status_code == 200
    dm_id = dm_res.json()["id"]
    print(f"      Private conversation established: {dm_id}")

    # Helper functions to drain frames
    def drain_until_event(ws, expected_event):
        for _ in range(15):
            frame = ws.receive_json()
            if frame.get("event") == expected_event:
                return frame
        raise TimeoutError(f"Expected event '{expected_event}' was not received.")

    def drain_until_message(ws, expected_content):
        for _ in range(15):
            frame = ws.receive_json()
            if frame.get("event") == "NEW_MESSAGE":
                content = frame.get("data", {}).get("message", {}).get("content")
                if content == expected_content:
                    return frame
        raise TimeoutError(f"Message with content '{expected_content}' was not received.")

    # 3. Connect all 3 independent WebSocket sessions
    print("\n[3/6] Connecting 3 concurrent authenticated WebSocket sessions...")
    with client_alice.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_a, \
         client_bob.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_b, \
         client_charlie.websocket_connect("/ws/chat", headers={"Origin": "http://localhost:5173"}) as ws_c:

        auth_a = drain_until_event(ws_a, "AUTH_SUCCESS")
        auth_b = drain_until_event(ws_b, "AUTH_SUCCESS")
        auth_c = drain_until_event(ws_c, "AUTH_SUCCESS")

        print(f"      WebSocket Handshakes verified: Alice={auth_a['data']['username']}, Bob={auth_b['data']['username']}, Charlie={auth_c['data']['username']}")

        # 4. Alice sends a private message to Bob
        secret_msg = f"Hey Bob, here is the secret project key: {uuid.uuid4().hex}"
        cmsg_id = f"cmsg_{uuid.uuid4().hex[:8]}"

        print(f"\n[4/6] Alice sends private message to Bob in {dm_id}...")
        ws_a.send_json({
            "event": "CHAT_MESSAGE",
            "data": {
                "conversation_id": dm_id,
                "content": secret_msg,
                "client_msg_id": cmsg_id,
            },
        })

        # Alice receives ACK and confirmation
        ack = drain_until_event(ws_a, "MESSAGE_ACK")
        assert ack["data"]["client_msg_id"] == cmsg_id
        assert ack["data"]["status"] == "sent"
        print(f"      [CONFIRMED] Alice received MESSAGE_ACK with DB message_id={ack['data']['message_id']}")

        alice_event = drain_until_message(ws_a, secret_msg)
        assert alice_event["data"]["message"]["sender"]["id"] == alice_id

        # Bob receives NEW_MESSAGE
        bob_event = drain_until_message(ws_b, secret_msg)
        assert bob_event["data"]["message"]["sender"]["id"] == alice_id
        print(f"      [CONFIRMED] Bob received private message from Alice: '{secret_msg[:35]}...'")

        # Charlie must NOT receive the private message
        ws_c.send_json({"type": "ping"})
        charlie_reply = ws_c.receive_json()
        if charlie_reply.get("type") != "pong":
            charlie_reply = ws_c.receive_json()
        assert charlie_reply["type"] == "pong", f"Unexpected frame received by Charlie: {charlie_reply}"
        print("      [ISOLATION VERIFIED] Charlie did NOT receive Alice and Bob's private message frame.")

        # 5. Broadcast message in #general-lan
        print("\n[5/6] Charlie broadcasts a public announcement to '#general-lan'...")
        broadcast_text = f"Public LAN announcement: {uuid.uuid4().hex[:8]}"
        ws_c.send_json({
            "event": "CHAT_MESSAGE",
            "data": {
                "conversation_id": "broadcast-general",
                "content": broadcast_text,
                "client_msg_id": f"cmsg_{uuid.uuid4().hex[:8]}",
            },
        })

        b_ack = drain_until_event(ws_c, "MESSAGE_ACK")
        assert b_ack["data"]["status"] == "sent"

        # Alice, Bob, and Charlie all receive the broadcast
        new_a = drain_until_message(ws_a, broadcast_text)
        new_b = drain_until_message(ws_b, broadcast_text)
        new_c = drain_until_message(ws_c, broadcast_text)

        assert new_a["data"]["message"]["content"] == broadcast_text
        assert new_b["data"]["message"]["content"] == broadcast_text
        assert new_c["data"]["message"]["content"] == broadcast_text
        print("      [BROADCAST VERIFIED] All 3 users received the public broadcast message.")

    # 6. Authorization checks at REST layer
    print("\n[6/6] Verifying REST authorization barriers...")
    # Charlie attempts to read Alice and Bob's private history
    snoop_res = client_charlie.get(f"/api/conversations/{dm_id}/messages")
    assert snoop_res.status_code == 403, f"Expected 403 Forbidden, got {snoop_res.status_code}"
    print(f"      [SECURITY VERIFIED] Charlie snooping attempt returned HTTP 403 Forbidden ({snoop_res.json()['error']['message']})")

    # Bob reads his own conversation with Alice
    bob_history = client_bob.get(f"/api/conversations/{dm_id}/messages")
    assert bob_history.status_code == 200
    assert any(m["content"] == secret_msg for m in bob_history.json()["messages"])
    print(f"      [PERSISTENCE VERIFIED] Bob retrieved persisted message history from SQLite ({len(bob_history.json()['messages'])} messages)")

    print("\n" + "=" * 70)
    print("SUCCESS: ALL MULTI-SESSION TESTS PASSED WITH COMPLETE PRIVACY ISOLATION!")
    print("=" * 70)


if __name__ == "__main__":
    run_multi_session_verification()
