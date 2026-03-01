from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.couriers.location_models import CourierLocation


class CourierLocationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.model = CourierLocation

    async def create(self, payload: dict) -> CourierLocation:
        obj = self.model(**payload)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def get_latest_for_courier(self, courier_user_id: int) -> CourierLocation | None:
        res = await self.db.execute(
            select(self.model)
            .where(self.model.courier_user_id == courier_user_id)
            .order_by(desc(self.model.created_at))
            .limit(1)
        )
        return res.scalar_one_or_none()

