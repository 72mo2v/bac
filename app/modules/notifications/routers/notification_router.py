from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.notifications.schemas import Notification
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.notifications.connection_manager import manager
from app.core.deps import get_current_active_user
from app.core.middleware import get_store_id
from app.modules.auth.schemas import User

router = APIRouter()


class MarkReadPayload(BaseModel):
    type: Optional[str] = None

async def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    repo = NotificationRepository(db)
    return NotificationService(repo)

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle client-to-server messages if needed
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

@router.get("", response_model=List[Notification])
@router.get("/", response_model=List[Notification])
async def list_notifications(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service)
):
    store_id = get_store_id()
    return await service.get_user_notifications(current_user.id, skip, limit, store_id=store_id)


@router.get("/unread-counts", response_model=Dict[str, int])
async def unread_counts(
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service),
):
    store_id = get_store_id()
    return await service.notification_repo.get_unread_counts_by_type(current_user.id, store_id=store_id)

@router.post("/mark-read")
async def mark_read(
    payload: Optional[MarkReadPayload] = Body(default=None),
    current_user: User = Depends(get_current_active_user),
    service: NotificationService = Depends(get_notification_service)
):
    store_id = get_store_id()
    if payload and payload.type:
        await service.notification_repo.mark_as_read(current_user.id, notif_type=payload.type, store_id=store_id)
    else:
        await service.notification_repo.mark_all_as_read(current_user.id)
    return {"status": "success"}
