import re
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import WebSocket
from ..config import settings
from ..logging_config import logger


class ConnectionManager:
    """Manages active WebSocket connections, origin validation, and presence tracking."""

    def __init__(self):
        # Maps user_id -> List[WebSocket] to support multi-tab/device sessions
        self.active_connections: Dict[int, List[WebSocket]] = {}

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Validate WebSocket Origin header against explicit allowed list and LAN regex."""
        if not origin:
            # Direct non-browser clients (CLI test scripts) might omit Origin
            return True

        # Check explicit origins
        if origin in settings.CORS_ORIGINS:
            return True

        # Check LAN subnet regex
        if settings.CORS_ORIGIN_REGEX and re.match(settings.CORS_ORIGIN_REGEX, origin):
            return True

        logger.warning(f"Rejected WebSocket connection from unauthorized origin: {origin}")
        return False

    def get_user_connection_count(self, user_id: int) -> int:
        return len(self.active_connections.get(user_id, []))

    def get_total_connection_count(self) -> int:
        return sum(len(conns) for conns in self.active_connections.values())

    async def connect(self, user_id: int, websocket: WebSocket) -> tuple[bool, str, bool]:
        """
        Register a new WebSocket connection for an authenticated user.
        Enforces MAX_CONNECTIONS_PER_USER and MAX_TOTAL_CONNECTIONS limits.
        Returns: (allowed: bool, reason: str, is_first_connection: bool)
        """
        user_conns = self.get_user_connection_count(user_id)
        if user_conns >= settings.MAX_CONNECTIONS_PER_USER:
            logger.warning(
                f"WebSocket rejected for user {user_id}: per-user connection limit "
                f"({settings.MAX_CONNECTIONS_PER_USER}) exceeded."
            )
            return False, f"Maximum concurrent connections ({settings.MAX_CONNECTIONS_PER_USER}) reached.", False

        total_conns = self.get_total_connection_count()
        if total_conns >= settings.MAX_TOTAL_CONNECTIONS:
            logger.warning(
                f"WebSocket rejected for user {user_id}: total server connection limit "
                f"({settings.MAX_TOTAL_CONNECTIONS}) reached."
            )
            return False, "Server is currently at maximum connection capacity.", False

        is_first_connection = user_conns == 0

        if user_id not in self.active_connections:
            self.active_connections[user_id] = []

        self.active_connections[user_id].append(websocket)
        logger.info(
            f"User {user_id} connected (socket count: {len(self.active_connections[user_id])}). "
            f"Total online users: {len(self.active_connections)}"
        )
        return True, "Connected successfully", is_first_connection

    def disconnect(self, user_id: int, websocket: WebSocket) -> bool:
        """
        Remove a WebSocket connection.
        Returns True if the user has no remaining active sockets (transitioned to OFFLINE).
        """
        is_now_offline = False

        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)

            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
                is_now_offline = True

        logger.info(
            f"User {user_id} disconnected. User offline: {is_now_offline}. "
            f"Total online users: {len(self.active_connections)}"
        )
        return is_now_offline

    def is_user_online(self, user_id: int) -> bool:
        """Check if a user currently has any active WebSocket connections."""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_socket_event(self, websocket: WebSocket, event_name: str, payload: dict):
        """Send a structured JSON event to a specific WebSocket instance."""
        message = {
            "event": event_name,
            "data": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send direct socket event '{event_name}': {e}")

    async def send_personal_event(self, user_id: int, event_name: str, payload: dict):
        """Send a structured JSON event to all active sockets of a specific user."""
        message = {
            "event": event_name,
            "data": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        sockets = self.active_connections.get(user_id, [])
        for ws in list(sockets):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to deliver personal event '{event_name}' to user {user_id}: {e}")

    async def send_to_users(self, user_ids: List[int], event_name: str, payload: dict):
        """Send a structured JSON event to all active sockets of a specific list of user IDs."""
        message = {
            "event": event_name,
            "data": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        for uid in user_ids:
            sockets = self.active_connections.get(uid, [])
            for ws in list(sockets):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to deliver event '{event_name}' to user {uid}: {e}")

    async def broadcast_event(self, event_name: str, payload: dict, exclude_user_id: Optional[int] = None):
        """Broadcast a structured JSON event to all currently connected peers, optionally excluding a user."""
        message = {
            "event": event_name,
            "data": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }
        for uid, sockets in list(self.active_connections.items()):
            if exclude_user_id is not None and uid == exclude_user_id:
                continue
            for ws in list(sockets):
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to deliver broadcast event to user {uid}: {e}")

    async def broadcast_presence(self, user_id: int, status: str, last_seen: Optional[str] = None):
        """Broadcast an online/offline presence change event."""
        await self.broadcast_event(
            "PRESENCE_CHANGE",
            {
                "user_id": user_id,
                "status": status,
                "last_seen": last_seen,
            },
        )


ws_manager = ConnectionManager()
