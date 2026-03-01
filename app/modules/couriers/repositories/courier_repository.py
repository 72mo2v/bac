from typing import List, Optional
from sqlalchemy import select
from app.core.base_repository import BaseRepository
from app.modules.couriers.models import Courier
from sqlalchemy.orm import joinedload
from app.core.middleware import get_store_id


class CourierRepository(BaseRepository[Courier]):
    def __init__(self, db):
        super().__init__(Courier, db)

    async def get(self, id: int) -> Optional[Courier]:
        query = select(Courier).options(joinedload(Courier.user)).filter(Courier.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


    async def update(self, db_obj: Courier, obj_in_data: dict) -> Courier:
        db_obj = await super().update(db_obj, obj_in_data)
        # Re-fetch or refresh with relationship
        return await self.get(db_obj.id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[Courier]:

        query = select(Courier).options(joinedload(Courier.user))

        store_id = get_store_id()
        if store_id:
            query = query.filter(Courier.store_id == store_id)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_user_id(self, user_id: int) -> Optional[Courier]:
        query = select(Courier).options(joinedload(Courier.user)).filter(Courier.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_available(self, store_id: Optional[int] = None) -> List[Courier]:
        query = select(Courier).options(joinedload(Courier.user)).filter(Courier.is_available == True)
        if store_id:
            query = query.filter(Courier.store_id == store_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

