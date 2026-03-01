from app.core.exceptions import BusinessRuleException, NotFoundException
from app.modules.couriers.repositories.courier_repository import CourierRepository
from app.modules.couriers.schemas import CourierCreate, CourierUpdate

class CourierService:
    def __init__(self, courier_repo: CourierRepository):
        self.courier_repo = courier_repo

    async def register_courier(self, courier_in: CourierCreate):
        existing = await self.courier_repo.get_by_user_id(courier_in.user_id)
        if existing:
            raise BusinessRuleException("User is already registered as a courier")
        
        new_courier = await self.courier_repo.create(courier_in.model_dump())
        return await self.courier_repo.get(new_courier.id)


    async def update_status(self, courier_id: int, update: CourierUpdate):
        courier = await self.courier_repo.get(courier_id)
        if not courier:
            raise NotFoundException("Courier not found")
        
        await self.courier_repo.update(courier, update.model_dump(exclude_unset=True))
        return await self.courier_repo.get(courier_id)

