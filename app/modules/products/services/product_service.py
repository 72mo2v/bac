import uuid

from app.core.exceptions import BusinessRuleException
from app.modules.products.repositories.product_repository import ProductRepository, InventoryRepository
from app.modules.products.schemas import ProductCreate, ProductUpdate, InventoryUpdate

class ProductService:
    def __init__(self, product_repo: ProductRepository, inventory_repo: InventoryRepository):
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo

    async def create_product(self, product_in: ProductCreate):
        product_data = product_in.model_dump()
        inventory_data = product_data.pop("inventory", None)

        slug = product_data.get("slug")
        if slug is None or str(slug).strip() in ["", "-"]:
            product_data["slug"] = f"prod-{uuid.uuid4().hex[:12]}"
        
        # Create product (BaseRepo handles store_id)
        product = await self.product_repo.create(product_data)
        
        # Create initial inventory
        if inventory_data:
            await self.inventory_repo.create({
                "product_id": product.id,
                "store_id": product.store_id,
                **inventory_data
            })
        else:
            await self.inventory_repo.create({
                "product_id": product.id,
                "store_id": product.store_id,
                "quantity": 0
            })
            
        return await self.product_repo.get_with_inventory(product.id)

    async def update_inventory(self, product_id: int, inventory_in: InventoryUpdate):
        product = await self.product_repo.get_with_inventory(product_id)
        if not product:
            raise BusinessRuleException("Product not found")
        
        if not product.inventory:
            # Should not happen typically, but as a fallback:
            return await self.inventory_repo.create({
                "product_id": product.id,
                **inventory_in.model_dump(exclude_unset=True)
            })
        
        return await self.inventory_repo.update(
            product.inventory, 
            inventory_in.model_dump(exclude_unset=True)
        )
