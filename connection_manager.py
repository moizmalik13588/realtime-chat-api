from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)
        print(f"User {user_id} connected. Devices: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: int, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            print(f"User {user_id} disconnected. Remaining devices: {len(self.active_connections.get(user_id, []))}")

    async def send_personal_message(self, user_id: int, message: str) -> bool:
        """
        Agar user ISI server pe kisi bhi device se connected hai, sabko bhej do.
        Return True agar kam se kam ek device ko bhej diya.
        """
        if user_id not in self.active_connections:
            return False

        delivered = False
        dead_connections = []

        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message)
                delivered = True
            except Exception:
                dead_connections.append(websocket)

        # Dead connections cleanup (agar send fail hua)
        for ws in dead_connections:
            self.active_connections[user_id].remove(ws)
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]

        return delivered

    def is_online(self, user_id: int) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def send_to_other_devices(self, user_id: int, sender_ws: WebSocket, message: str):
        """
        Sender ke apne doosre devices (websocket ke alawa jisne bheja) ko bhi
        message sync karta hai, taaki har device pe conversation up-to-date rahe.
        """
        if user_id not in self.active_connections:
            return

        for websocket in self.active_connections[user_id]:
            if websocket is not sender_ws:
                try:
                    await websocket.send_text(message)
                except Exception:
                    pass  
manager = ConnectionManager()