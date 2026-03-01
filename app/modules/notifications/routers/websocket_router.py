from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import jwt, JWTError
from app.core.config import settings
from app.core.security import ALGORITHM
from app.modules.notifications.connection_manager import manager

router = APIRouter()

async def get_user_id_from_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except (JWTError, ValueError):
        return None

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user_id = await get_user_id_from_token(token)
    if user_id is None:
        await websocket.close(code=4001) # Unauthorized
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive and listen for any client messages if needed
            data = await websocket.receive_text()
            # Handle incoming data if necessary
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
