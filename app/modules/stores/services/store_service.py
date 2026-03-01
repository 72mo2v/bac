from app.core.exceptions import BusinessRuleException
from app.modules.stores.repositories.store_repository import StoreRepository
from app.modules.stores.schemas import StoreCreate, StoreUpdate

class StoreService:
    def __init__(self, store_repo: StoreRepository):
        self.store_repo = store_repo

    async def create_store(self, store_in: StoreCreate):
        existing = await self.store_repo.get_by_slug(store_in.slug)
        if existing:
            raise BusinessRuleException("Store with this slug already exists")
        
        return await self.store_repo.create(store_in.model_dump())

    async def get_store(self, store_id: int):
        store = await self.store_repo.get(store_id)
        if not store:
            raise BusinessRuleException("Store not found")
        return store

    async def update_store(self, store_id: int, store_update: StoreUpdate):
        store = await self.get_store(store_id)
        return await self.store_repo.update(store, store_update.model_dump(exclude_unset=True))
