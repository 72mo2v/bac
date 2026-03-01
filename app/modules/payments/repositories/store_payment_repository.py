from typing import List, Optional
from sqlalchemy import select
from app.core.base_repository import BaseRepository
from app.modules.payments.models import StorePaymentMethod

class StorePaymentMethodRepository(BaseRepository[StorePaymentMethod]):
    def __init__(self, db):
        super().__init__(StorePaymentMethod, db)

    async def get_by_store(self, store_id: int, enabled_only: bool = False) -> List[StorePaymentMethod]:
        query = select(StorePaymentMethod).filter(StorePaymentMethod.store_id == store_id)
        if enabled_only:
            query = query.filter(StorePaymentMethod.is_enabled == True)
        result = await self.db.execute(query)
        return list(result.scalars().all())
