from typing import Optional
from sqlalchemy import select
from app.core.base_repository import BaseRepository
from app.modules.stores.models import Store

class StoreRepository(BaseRepository[Store]):
    def __init__(self, db):
        super().__init__(Store, db)

    async def get_by_slug(self, slug: str) -> Optional[Store]:
        query = select(Store).filter(Store.slug == slug)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
