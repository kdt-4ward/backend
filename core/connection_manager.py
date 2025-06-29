from fastapi import WebSocket
from typing import Dict, Tuple, Optional
from core.redis import save_couple_mapping, load_couple_mapping

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.couple_map: Dict[str, Tuple[str, str]] = {}
        self.user_to_couple: Dict[str, str] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        self.user_to_couple.pop(user_id, None)

    def get_partner(self, user_id: str) -> Optional[str]:
        couple_id = self.user_to_couple.get(user_id)
        if not couple_id:
            return None
        u1, u2 = self.couple_map.get(couple_id, (None, None))
        return u2 if u1 == user_id else u1

    def get_couple_id(self, user_id: str) -> Optional[str]:
        return self.user_to_couple.get(user_id)

    def is_couple_ready(self, user_id: str) -> bool:
        partner_id = self.get_partner(user_id)
        return partner_id in self.active_connections

    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections

    async def send_personal_message(self, message: str, to_user_id: str):
        if to_user_id in self.active_connections:
            await self.active_connections[to_user_id].send_text(message)

    async def send_personal_json(self, data: dict, to_user_id: str):
        if to_user_id in self.active_connections:
            await self.active_connections[to_user_id].send_json(data)

    async def broadcast_status(self, user_id, status):
        couple_id = self.get_couple_id(user_id)
        if not couple_id:
            return

        for target_id, conn in self.active_connections.items():
            if self.get_couple_id(target_id) == couple_id:
                await conn.send_json({"type": "status", "user": user_id, "status": status})

    def register_couple(self, user_id: str, partner_id: str, couple_id: str):
        self.couple_map[couple_id] = (user_id, partner_id)
        self.user_to_couple[user_id] = couple_id
        self.user_to_couple[partner_id] = couple_id
        save_couple_mapping(user_id, partner_id, couple_id)

    def auto_register_from_redis(self, user_id: str):
        couple_id, partner_id = load_couple_mapping(user_id)
        if not couple_id or not partner_id:
            return
        self.user_to_couple[user_id] = couple_id
        if couple_id not in self.couple_map:
            self.couple_map[couple_id] = (user_id, partner_id)
