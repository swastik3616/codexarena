import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set

app = FastAPI(title="CodexArena API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Room State Manager
class RoomManager:
    def __init__(self):
        # Maps roomId -> set of active WebSockets
        self.active_rooms: Dict[str, Set[WebSocket]] = {}
        # Maps WebSocket -> candidate info (id, name, etc.)
        self.candidate_metadata: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, room_id: str, candidate_name: str) -> str:
        await websocket.accept()
        
        # Generate unique ID for candidate
        candidate_id = str(uuid.uuid4())
        
        if room_id not in self.active_rooms:
            self.active_rooms[room_id] = set()
            
        self.active_rooms[room_id].add(websocket)
        self.candidate_metadata[websocket] = {
            "id": candidate_id,
            "name": candidate_name,
            "room_id": room_id
        }
        
        return candidate_id

    def disconnect(self, websocket: WebSocket):
        if websocket in self.candidate_metadata:
            meta = self.candidate_metadata.pop(websocket)
            room_id = meta["room_id"]
            if room_id in self.active_rooms:
                self.active_rooms[room_id].remove(websocket)
                if not self.active_rooms[room_id]:
                    self.active_rooms.pop(room_id, None)

    async def broadcast_to_room(self, message: dict, room_id: str):
        if room_id in self.active_rooms:
            for connection in self.active_rooms[room_id]:
                await connection.send_json(message)

manager = RoomManager()

@app.get("/")
def read_root():
    return {"message": "CodexArena Backend Running"}

# Candidate WebSocket Endpoint
@app.websocket("/ws/room/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, candidate_name: str):
    candidate_id = await manager.connect(websocket, room_id, candidate_name)
    
    # Notify room that a new candidate joined
    await manager.broadcast_to_room(
        {
            "type": "candidate_joined", 
            "candidate_id": candidate_id, 
            "candidate_name": candidate_name
        }, 
        room_id
    )

    try:
        while True:
            # Receive candidate keyboard strokes / code updates
            data = await websocket.receive_json()
            
            # Broadcast state (e.g. code update, tab switch) to recruiter dashboard
            await manager.broadcast_to_room(
                {
                    "type": data.get("type", "update"),
                    "candidate_id": candidate_id,
                    "payload": data
                },
                room_id
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast_to_room(
            {
                "type": "candidate_left", 
                "candidate_id": candidate_id,
                "candidate_name": candidate_name
            }, 
            room_id
        )