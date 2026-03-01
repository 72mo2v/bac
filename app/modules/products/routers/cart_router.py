from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.modules.products.schemas import Cart, CartItem, CartItemCreate
from app.modules.products.repositories.cart_repository import CartRepository, CartItemRepository
from app.modules.products.services.cart_service import CartService

from app.modules.products.repositories.product_repository import ProductRepository

router = APIRouter()

async def get_cart_service(db: AsyncSession = Depends(get_db)) -> CartService:
    cart_repo = CartRepository(db)
    item_repo = CartItemRepository(db)
    prod_repo = ProductRepository(db)
    return CartService(cart_repo, item_repo, prod_repo)

# Mock user id
async def get_current_user_id() -> int:
    return 1

@router.get("/", response_model=Cart)
async def get_cart(
    user_id: int = Depends(get_current_user_id),
    service: CartService = Depends(get_cart_service)
):
    return await service.get_cart(user_id)

@router.post("/items", response_model=Cart)
async def add_to_cart(
    item: CartItemCreate,
    user_id: int = Depends(get_current_user_id),
    service: CartService = Depends(get_cart_service)
):
    return await service.add_item(user_id, item)

@router.delete("/items/{product_id}", response_model=Cart)
async def remove_from_cart(
    product_id: int,
    user_id: int = Depends(get_current_user_id),
    service: CartService = Depends(get_cart_service)
):
    return await service.remove_item(user_id, product_id)

@router.delete("/", status_code=204)
async def clear_cart(
    user_id: int = Depends(get_current_user_id),
    service: CartService = Depends(get_cart_service)
):
    await service.clear_cart(user_id)
    return None
