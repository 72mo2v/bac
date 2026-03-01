from typing import List, Optional
from app.core.exceptions import BusinessRuleException, NotFoundException
from app.modules.payments.repositories.store_payment_repository import StorePaymentMethodRepository
from app.modules.payments.schemas import StorePaymentMethodCreate, StorePaymentMethodUpdate
from app.modules.payments.models import StorePaymentMethod

class StorePaymentMethodService:
    def __init__(self, repository: StorePaymentMethodRepository):
        self.repository = repository

    async def get_methods_for_store(self, store_id: int, enabled_only: bool = False) -> List[StorePaymentMethod]:
        return await self.repository.get_by_store(store_id, enabled_only)

    async def create_method(self, store_id: int, method_in: StorePaymentMethodCreate) -> StorePaymentMethod:
        data = method_in.model_dump()
        data["store_id"] = store_id
        return await self.repository.create(data)

    async def update_method(self, store_id: int, method_id: int, method_in: StorePaymentMethodUpdate) -> StorePaymentMethod:
        method = await self.repository.get(method_id)
        if not method or method.store_id != store_id:
            raise NotFoundException("Store Payment Method not found")
        
        return await self.repository.update(method, method_in.model_dump(exclude_unset=True))

    async def delete_method(self, store_id: int, method_id: int):
        method = await self.repository.get(method_id)
        if not method or method.store_id != store_id:
            raise NotFoundException("Store Payment Method not found")
        
        await self.repository.remove(method_id)
