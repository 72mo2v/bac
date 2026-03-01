from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import PushToken


class PushTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = PushToken

    async def upsert(self, *, user_id: int, token: str, platform: str) -> PushToken:
        res = await self.db.execute(
            select(self.model).where(self.model.user_id == int(user_id), self.model.token == str(token))
        )
        existing = res.scalar_one_or_none()
        if existing:
            existing.platform = str(platform)
            return existing

        obj = self.model(user_id=int(user_id), token=str(token), platform=str(platform))
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def delete(self, *, user_id: int, token: str) -> int:
        res = await self.db.execute(
            select(self.model).where(self.model.user_id == int(user_id), self.model.token == str(token))
        )
        existing = res.scalar_one_or_none()
        if not existing:
            return 0
        await self.db.delete(existing)
        return 1

    async def list_for_user(self, *, user_id: int) -> List[PushToken]:
        res = await self.db.execute(select(self.model).where(self.model.user_id == int(user_id)))
        return list(res.scalars().all())

