from app.core.exceptions import BusinessRuleException, NotFoundException
from app.modules.products.repositories.cart_repository import CartRepository, CartItemRepository
from app.modules.products.repositories.product_repository import ProductRepository
from app.modules.products.schemas import CartItemCreate

class CartService:
    def __init__(self, cart_repo: CartRepository, item_repo: CartItemRepository, product_repo: ProductRepository):
        self.cart_repo = cart_repo
        self.item_repo = item_repo
        self.product_repo = product_repo

    async def get_cart(self, user_id: int):
        return await self.cart_repo.get_or_create(user_id)

    async def add_item(self, user_id: int, item_in: CartItemCreate):
        # Validate product existence
        product = await self.product_repo.get(item_in.product_id)
        if not product:
            raise NotFoundException(f"Product with id {item_in.product_id} not found")
            
        cart = await self.cart_repo.get_or_create(user_id)
        
        existing_item = await self.item_repo.get_item(cart.id, item_in.product_id)
        if existing_item:
            existing_item.quantity += item_in.quantity
            await self.item_repo.update(existing_item, {})
        else:
            await self.item_repo.create({
                "cart_id": cart.id,
                "product_id": item_in.product_id,
                "quantity": item_in.quantity
            })
            
        return await self.cart_repo.get_by_user_id(user_id)

    async def remove_item(self, user_id: int, product_id: int):
        cart = await self.cart_repo.get_by_user_id(user_id)
        if cart:
            item = await self.item_repo.get_item(cart.id, product_id)
            if item:
                await self.item_repo.remove(item.id)
        return await self.cart_repo.get_by_user_id(user_id)

    async def clear_cart(self, user_id: int):
        cart = await self.cart_repo.get_by_user_id(user_id)
        if cart:
            for item in cart.items:
                await self.item_repo.remove(item.id)
