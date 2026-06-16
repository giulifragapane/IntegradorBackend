# app/core/websocket.py
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("app.core.websocket")


class ConnectionManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = {}
        self.socket_rooms: dict[WebSocket, set[str]] = {}

    async def connect(self, websocket: WebSocket, role: str, user_id: int) -> None:
        await websocket.accept()
        self._join_room(websocket, self._role_room(role))
        logger.info("WebSocket conectado. user_id=%s role=%s", user_id, role)

    def disconnect(self, websocket: WebSocket) -> None:
        rooms = self.socket_rooms.pop(websocket, set())

        for room in rooms:
            if room in self.rooms:
                self.rooms[room].discard(websocket)
                if not self.rooms[room]:
                    del self.rooms[room]

        logger.info("WebSocket desconectado. rooms=%s", rooms)

    def join_order_room(self, websocket: WebSocket, order_id: int) -> None:
        self._join_room(websocket, self._order_room(order_id))

    def leave_order_room(self, websocket: WebSocket, order_id: int) -> None:
        room = self._order_room(order_id)

        if room not in self.rooms:
            return

        self.rooms[room].discard(websocket)

        if websocket in self.socket_rooms:
            self.socket_rooms[websocket].discard(room)

        if not self.rooms[room]:
            del self.rooms[room]

    async def broadcast_to_role(
        self,
        role: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        await self._emit_to_room(self._role_room(role), event_type, data)

    async def broadcast_to_roles(
        self,
        roles: list[str],
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        sent_to: set[WebSocket] = set()
        payload = self._build_payload(event_type, data)

        for role in roles:
            room = self._role_room(role)
            for connection in list(self.rooms.get(room, set())):
                if connection in sent_to:
                    continue

                try:
                    await connection.send_json(payload)
                    sent_to.add(connection)
                except Exception as exc:
                    logger.warning("Error enviando WebSocket a rol %s: %s", role, exc)
                    self.disconnect(connection)

    async def broadcast_to_order(
        self,
        order_id: int,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        await self._emit_to_room(self._order_room(order_id), event_type, data)

    async def broadcast(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        sent_to: set[WebSocket] = set()
        payload = self._build_payload(event_type, data or {})

        for connections in list(self.rooms.values()):
            for connection in list(connections):
                if connection in sent_to:
                    continue

                try:
                    await connection.send_json(payload)
                    sent_to.add(connection)
                except Exception as exc:
                    logger.warning("Error enviando WebSocket global: %s", exc)
                    self.disconnect(connection)

    def get_active_connections_count(self) -> int:
        return len(self.socket_rooms)

    def get_rooms_info(self) -> dict[str, int]:
        return {room: len(connections) for room, connections in self.rooms.items()}

    def _join_room(self, websocket: WebSocket, room: str) -> None:
        if room not in self.rooms:
            self.rooms[room] = set()

        self.rooms[room].add(websocket)

        if websocket not in self.socket_rooms:
            self.socket_rooms[websocket] = set()

        self.socket_rooms[websocket].add(room)

    async def _emit_to_room(
        self,
        room: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        payload = self._build_payload(event_type, data)

        for connection in list(self.rooms.get(room, set())):
            try:
                await connection.send_json(payload)
            except Exception as exc:
                logger.warning("Error enviando WebSocket a room %s: %s", room, exc)
                self.disconnect(connection)

    def _build_payload(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event": event_type,
            "type": event_type,
            "data": data,
        }

        if "pedido" in data:
            payload["pedido"] = data["pedido"]

        return payload

    def _role_room(self, role: str) -> str:
        return f"role:{role.upper()}"

    def _order_room(self, order_id: int) -> str:
        return f"order:{order_id}"


manager = ConnectionManager()
websocket_manager = manager
