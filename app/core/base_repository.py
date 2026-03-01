from typing import Generic, Type, TypeVar, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from app.core.database import Base
from app.core.middleware import get_store_id

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        query = select(self.model).filter(self.model.id == id)
        
        # Enforce tenant isolation if model has store_id
        if hasattr(self.model, "store_id"):
            store_id = get_store_id()
            if store_id:
                query = query.filter(self.model.store_id == store_id)
                
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self) -> List[ModelType]:
        query = select(self.model)
        if hasattr(self.model, "store_id"):
            store_id = get_store_id()
            if store_id:
                query = query.filter(self.model.store_id == store_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        query = select(self.model).offset(skip).limit(limit)
        
        if hasattr(self.model, "store_id"):
            store_id = get_store_id()
            if store_id:
                query = query.filter(self.model.store_id == store_id)
                
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_in_data: dict) -> ModelType:
        # Automatically inject store_id if model supports it and context has it
        if hasattr(self.model, "store_id") and ("store_id" not in obj_in_data or obj_in_data.get("store_id") is None):
            store_id = get_store_id()
            if store_id:
                obj_in_data["store_id"] = store_id
                
        db_obj = self.model(**obj_in_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: ModelType, obj_in_data: dict) -> ModelType:
        for field in obj_in_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_in_data[field])
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def remove(self, id: Any) -> Optional[ModelType]:
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.flush()
        return obj
