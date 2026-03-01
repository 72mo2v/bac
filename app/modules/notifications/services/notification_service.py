from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.modules.notifications.schemas import NotificationCreate
from app.modules.notifications.connection_manager import manager

class NotificationService:
    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    async def notify_user(self, user_id: int, title: str, message: str, data: dict = None, type: str = None, store_id: int = None):
        # 1. Save to database
        notification = await self.notification_repo.create({
            "user_id": user_id,
            "title": title,
            "message": message,
            "data": data,
            "type": type,
            "store_id": store_id,
        })

        # Persist notification so it appears in GET /notifications
        await self.notification_repo.db.commit()
        
        # 2. Send via WebSocket if user is online
        ui_type = type if type in ["info", "warning", "success"] else "info"
        await manager.send_personal_message({
            "type": ui_type,
            "id": notification.id,
            "title": title,
            "message": message,
            "data": data,
            "category": type,
            "store_id": store_id,
            "created_at": str(notification.created_at)
        }, user_id)
        
        return notification

    async def get_user_notifications(self, user_id: int, skip: int = 0, limit: int = 20, store_id: int = None):
        # BaseRepo get_multi logic or custom filter
        from sqlalchemy import select
        query = select(self.notification_repo.model).filter(
            self.notification_repo.model.user_id == user_id
        ).order_by(self.notification_repo.model.created_at.desc()).offset(skip).limit(limit)

        if store_id:
            query = query.filter(self.notification_repo.model.store_id == store_id)
        
        result = await self.notification_repo.db.execute(query)
        return list(result.scalars().all())
