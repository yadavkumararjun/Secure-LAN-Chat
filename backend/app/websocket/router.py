import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from ..database import SessionLocal
from ..config import settings
from ..models import User
from ..logging_config import logger
from ..security.sessions import get_ws_authenticated_user
from ..services.rate_limiter import chat_rate_limiter
from ..services import chat_service
from ..schemas.chat import WebSocketChatMessagePayload, WebSocketTypingPayload
from .manager import ws_manager

router = APIRouter(tags=["WebSocket Real-Time Chat & Presence"])


async def handle_websocket_session(websocket: WebSocket, endpoint_name: str = "/ws/chat"):
    """
    Core WebSocket session handler supporting:
    - Origin verification (mitigates Cross-Site WebSocket Hijacking).
    - Session authentication via HTTP-only cookie.
    - Server-enforced identity (clients cannot spoof sender name or ID).
    - Real-time online/offline presence tracking with automatic cleanup.
    - Private one-to-one messaging with recipient isolation.
    - LAN broadcast messaging with public transparency.
    - Message deduplication (idempotent retry recovery).
    - Per-user rate limiting against flooding.
    - Graceful error responses on malformed frames.
    """
    # 1. Validate Origin header
    origin = websocket.headers.get("origin")
    if not ws_manager.is_origin_allowed(origin):
        logger.warning(f"Closing {endpoint_name}: unauthorized origin '{origin}'")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized origin")
        return

    # 2. Authenticate user from HTTP-only session cookie
    with SessionLocal() as auth_db:
        user = get_ws_authenticated_user(websocket, auth_db)
        if not user:
            logger.warning(f"Closing {endpoint_name}: missing or invalid session cookie")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized session")
            return

        user_id = user.id
        username = user.username
        display_name = user.display_name
        avatar = user.avatar or username[:2].upper()

    try:
        # 3. Accept WebSocket connection
        await websocket.accept()

        # 4. Register connection in manager (enforcing connection limits)
        allowed, reason, is_first_connection = await ws_manager.connect(user_id, websocket)
        if not allowed:
            await ws_manager.send_socket_event(
                websocket,
                "ERROR",
                {"code": "CONNECTION_LIMIT_EXCEEDED", "message": reason},
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=reason)
            return

        # 5. Send verified identity confirmation directly to client
        now_iso = datetime.utcnow().isoformat()
        await ws_manager.send_socket_event(
            websocket,
            "AUTH_SUCCESS",
            {
                "user_id": user_id,
                "username": username,
                "display_name": display_name,
                "avatar": avatar,
                "is_online": True,
            },
        )

        # 6. Broadcast presence transition if user just came online
        if is_first_connection:
            with SessionLocal() as presence_db:
                u = presence_db.query(User).filter(User.id == user_id).first()
                if u:
                    u.last_seen = datetime.utcnow()
                    presence_db.commit()
            await ws_manager.broadcast_presence(user_id=user_id, status="online", last_seen=now_iso)

        # 7. Inbound frame processing loop
        while True:
            raw_text = await websocket.receive_text()

            # Enforce maximum frame size to mitigate buffer exhaustion attacks
            if len(raw_text) > settings.MAX_WS_FRAME_SIZE_BYTES:
                await ws_manager.send_socket_event(
                    websocket,
                    "ERROR",
                    {
                        "code": "MESSAGE_TOO_LARGE",
                        "message": f"Frame size ({len(raw_text)} bytes) exceeds maximum limit of {settings.MAX_WS_FRAME_SIZE_BYTES} bytes.",
                    },
                )
                continue

            try:
                frame = json.loads(raw_text)
            except Exception:
                await ws_manager.send_socket_event(
                    websocket,
                    "ERROR",
                    {
                        "code": "INVALID_JSON",
                        "message": "Incoming message frame must be valid JSON.",
                    },
                )
                continue

            if not isinstance(frame, dict):
                await ws_manager.send_socket_event(
                    websocket,
                    "ERROR",
                    {
                        "code": "INVALID_FRAME",
                        "message": "Message frame must be a JSON object.",
                    },
                )
                continue

            # Support legacy or simple ping/pong
            if frame.get("type") == "ping" or frame.get("event") == "PING":
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                continue

            event_name = frame.get("event")
            data = frame.get("data", {})

            # ---------------------------------------------------------
            # Event: CHAT_MESSAGE
            # ---------------------------------------------------------
            if event_name == "CHAT_MESSAGE":
                client_msg_id = data.get("client_msg_id") if isinstance(data, dict) else None

                # Rate Limiting Guard
                if not chat_rate_limiter.is_allowed(user_id):
                    await ws_manager.send_socket_event(
                        websocket,
                        "ERROR",
                        {
                            "client_msg_id": client_msg_id,
                            "code": "RATE_LIMITED",
                            "message": "You are sending messages too quickly. Please wait a moment.",
                        },
                    )
                    continue

                # Schema Validation
                try:
                    chat_payload = WebSocketChatMessagePayload.model_validate(data)
                except ValidationError as val_err:
                    err_msg = val_err.errors()[0]["msg"] if val_err.errors() else "Invalid message payload."
                    await ws_manager.send_socket_event(
                        websocket,
                        "ERROR",
                        {
                            "client_msg_id": client_msg_id,
                            "code": "INVALID_PAYLOAD",
                            "message": err_msg,
                        },
                    )
                    continue

                # Conversation Membership, Authorization & Persist
                try:
                    with SessionLocal() as db:
                        conv = chat_service.verify_conversation_access(db, user_id, chat_payload.conversation_id)
                        msg, is_new = chat_service.save_message(
                            db=db,
                            sender_id=user_id,
                            conversation_id=chat_payload.conversation_id,
                            content=chat_payload.content,
                            client_msg_id=chat_payload.client_msg_id,
                            message_type=chat_payload.message_type,
                        )
                        msg_id = msg.id
                        conv_id = msg.conversation_id
                        msg_content = msg.content
                        msg_type = msg.message_type
                        msg_client_id = msg.client_msg_id
                        msg_created_iso = msg.created_at.isoformat()
                        conv_type = conv.type
                        member_ids = (
                            chat_service.get_conversation_member_ids(db, msg.conversation_id)
                            if conv_type != "broadcast"
                            else []
                        )
                except Exception as op_err:
                    err_code = getattr(op_err, "code", getattr(op_err, "error_code", "SAVE_ERROR"))
                    err_msg = getattr(op_err, "message", str(op_err))
                    await ws_manager.send_socket_event(
                        websocket,
                        "ERROR",
                        {
                            "client_msg_id": client_msg_id,
                            "code": err_code,
                            "message": err_msg,
                        },
                    )
                    continue

                # Send delivery acknowledgment strictly back to sender
                await ws_manager.send_socket_event(
                    websocket,
                    "MESSAGE_ACK",
                    {
                        "client_msg_id": chat_payload.client_msg_id,
                        "message_id": msg_id,
                        "conversation_id": chat_payload.conversation_id,
                        "status": "sent",
                        "created_at": msg_created_iso,
                    },
                )

                # Dispatch NEW_MESSAGE event if newly persisted
                if is_new:
                    serialized_msg = {
                        "id": msg_id,
                        "conversation_id": conv_id,
                        "sender": {
                            "id": user_id,
                            "username": username,
                            "display_name": display_name,
                            "avatar": avatar,
                        },
                        "content": msg_content,
                        "message_type": msg_type,
                        "client_msg_id": msg_client_id,
                        "created_at": msg_created_iso,
                    }
                    event_payload = {
                        "message": serialized_msg,
                        "conversation_id": conv_id,
                    }

                    if conv_type == "broadcast":
                        await ws_manager.broadcast_event("NEW_MESSAGE", event_payload)
                    else:
                        await ws_manager.send_to_users(member_ids, "NEW_MESSAGE", event_payload)

            # ---------------------------------------------------------
            # Event: TYPING_INDICATOR
            # ---------------------------------------------------------
            elif event_name == "TYPING_INDICATOR":
                try:
                    typing_payload = WebSocketTypingPayload.model_validate(data)
                    with SessionLocal() as db:
                        conv = chat_service.verify_conversation_access(db, user_id, typing_payload.conversation_id)
                        conv_type = conv.type
                        conv_id = conv.id
                        target_members = (
                            [m for m in chat_service.get_conversation_member_ids(db, conv_id) if m != user_id]
                            if conv_type != "broadcast"
                            else []
                        )

                    out_payload = {
                        "conversation_id": typing_payload.conversation_id,
                        "user_id": user_id,
                        "username": username,
                        "is_typing": typing_payload.is_typing,
                    }
                    if conv_type == "broadcast":
                        await ws_manager.broadcast_event("TYPING_INDICATOR", out_payload, exclude_user_id=user_id)
                    else:
                        await ws_manager.send_to_users(target_members, "TYPING_INDICATOR", out_payload)
                except Exception:
                    pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected cleanly for user {user_id} ({username}) on {endpoint_name}")
    except Exception as e:
        logger.warning(f"WebSocket connection error on {endpoint_name}: {e}")
    finally:
        # Clean up connection & broadcast offline status if no remaining sockets
        if "user_id" in locals():
            is_now_offline = ws_manager.disconnect(user_id, websocket)
            if is_now_offline:
                now_iso = datetime.utcnow().isoformat()
                with SessionLocal() as db:
                    user_record = db.query(User).filter(User.id == user_id).first()
                    if user_record:
                        user_record.last_seen = datetime.utcnow()
                        db.commit()
                await ws_manager.broadcast_presence(user_id=user_id, status="offline", last_seen=now_iso)


@router.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """Primary WebSocket endpoint for real-time chat messaging, presence, and events."""
    await handle_websocket_session(websocket, endpoint_name="/ws/chat")


@router.websocket("/ws/presence")
async def websocket_presence_endpoint(websocket: WebSocket):
    """Presence & peer notification WebSocket endpoint (compatible with Phase 3 clients)."""
    await handle_websocket_session(websocket, endpoint_name="/ws/presence")
