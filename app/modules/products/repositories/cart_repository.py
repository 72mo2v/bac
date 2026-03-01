from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload, selectinload
from app.core.base_repository import BaseRepository
from app.modules.products.models import Cart, CartItem
from app.modules.products.schemas import CartItem as CartItemSchema

class CartRepository(BaseRepository[Cart]):
    def __init__(self, db):
        super().__init__(Cart, db)

    async def get_by_user_id(self, user_id: int) -> Optional[Cart]:
        query = select(Cart).options(
            selectinload(Cart.items).joinedload(CartItem.product)
        ).filter(Cart.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> Cart:
        cart = await self.get_by_user_id(user_id)
        if not cart:
            await self.create({"user_id": user_id})
            # Re-fetch to ensure relationships are loaded according to get_by_user_id logic
            cart = await self.get_by_user_id(user_id)
        return cart

class CartItemRepository(BaseRepository[CartItem]):
    def __init__(self, db):
        super().__init__(CartItem, db)

    async def get_item(self, cart_id: int, product_id: int) -> Optional[CartItem]:
        query = select(CartItem).filter(
            CartItem.cart_id == cart_id, 
            CartItem.product_id == product_id
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
