from typing import Dict, Optional
from sqlalchemy import select, update, func
from app.core.base_repository import BaseRepository
from app.modules.notifications.models import Notification

class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db):
        super().__init__(Notification, db)

    async def get_unread_count(self, user_id: int) -> int:
        query = select(Notification).filter(
            Notification.user_id == user_id, 
            Notification.is_read == False
        )
        result = await self.db.execute(query)
        return len(result.scalars().all())

    async def get_unread_counts_by_type(self, user_id: int, store_id: Optional[int] = None) -> Dict[str, int]:
        query = (
            select(Notification.type, func.count(Notification.id))
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)
            .group_by(Notification.type)
        )
        if store_id:
            query = query.where(Notification.store_id == store_id)
        result = await self.db.execute(query)

        counts: Dict[str, int] = {}
        for notif_type, cnt in result.all():
            key = str(notif_type) if notif_type is not None else "unknown"
            counts[key] = int(cnt or 0)
        return counts

    async def mark_all_as_read(self, user_id: int):
        query = update(Notification).where(
            Notification.user_id == user_id
        ).values(is_read=True)
        await self.db.execute(query)
        await self.db.flush()

    async def mark_as_read(self, user_id: int, notif_type: Optional[str] = None, store_id: Optional[int] = None):
        query = update(Notification).where(Notification.user_id == user_id)
        if store_id:
            query = query.where(Notification.store_id == store_id)
        if notif_type:
            query = query.where(Notification.type == notif_type)
        query = query.values(is_read=True)
        await self.db.execute(query)
        await self.db.flush()
