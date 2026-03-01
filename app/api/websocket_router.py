from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio

router = APIRouter()

# In-memory store for demo (replace with Redis/pubsub in prod)
active_connections: Dict[str, WebSocket] = {}

@router.websocket("/ws/order/{order_id}")
async def order_tracking_ws(websocket: WebSocket, order_id: int):
    await websocket.accept()
    key = f"order:{order_id}:{id(websocket)}"
    active_connections[key] = websocket
    try:
        while True:
            await asyncio.sleep(60)  # Keep alive
    except WebSocketDisconnect:
        del active_connections[key]

# Broadcast location update to all clients tracking this order
async def broadcast_order_location(order_id: int, location: dict):
    for key, ws in list(active_connections.items()):
        if key.startswith(f"order:{order_id}:"):
            try:
                await ws.send_json({"type": "location_update", "location": location})
            except Exception:
                del active_connections[key]
