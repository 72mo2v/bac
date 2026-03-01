from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from app.core.base_repository import BaseRepository
from app.modules.products.models import Product, Category, Inventory, ProductReview, ProductImage
from app.core.middleware import get_store_id

class ProductRepository(BaseRepository[Product]):
    def __init__(self, db):
        super().__init__(Product, db)

    async def get_with_inventory(self, id: int) -> Optional[Product]:
        store_id = get_store_id()
        query = select(Product).options(
            joinedload(Product.inventory),
            joinedload(Product.category),
            joinedload(Product.store),
            selectinload(Product.reviews).selectinload(ProductReview.user),
            selectinload(Product.images),
        ).filter(Product.id == id)
        if store_id:
            query = query.filter(Product.store_id == store_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_with_inventory(
        self, 
        skip: int = 0, 
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[int] = None
    ) -> List[Product]:
        store_id = get_store_id()
        query = select(Product).options(
            joinedload(Product.inventory),
            joinedload(Product.category),
            joinedload(Product.store),
            selectinload(Product.reviews).selectinload(ProductReview.user),
            selectinload(Product.images),
        )
        
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))
        
        if category_id:
            query = query.filter(Product.category_id == category_id)
            
        if store_id:
            query = query.filter(Product.store_id == store_id)
            
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db):
        super().__init__(Category, db)

class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, db):
        super().__init__(Inventory, db)

class ProductReviewRepository(BaseRepository[ProductReview]):
    def __init__(self, db):
        super().__init__(ProductReview, db)


class ProductImageRepository(BaseRepository[ProductImage]):
    def __init__(self, db):
        super().__init__(ProductImage, db)
