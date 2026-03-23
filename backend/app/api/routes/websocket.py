from __future__ import annotations

from fastapi import APIRouter, WebSocket

from app.services.realtime.websocket_hub import websocket_endpoint

router = APIRouter()


@router.websocket("/ws/{room_id}")
async def ws_room(websocket: WebSocket, room_id: str) -> None:
    await websocket_endpoint(websocket=websocket, room_id=room_id)

