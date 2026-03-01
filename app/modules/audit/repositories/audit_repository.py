from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.audit.models import AuditLog
from app.core.base_repository import BaseRepository

class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def get_recent_logs(self, limit: int = 100):
        query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def log_action(
        self, 
        admin_id: int, 
        action: str, 
        target_type: str, 
        target_id: str = None, 
        changes: dict = None, 
        ip_address: str = None
    ):
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            changes=changes,
            ip_address=ip_address
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log
