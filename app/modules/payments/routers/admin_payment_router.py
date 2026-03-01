from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.payments.subscription_schemas import (
    SubscriptionPaymentMethod, 
    SubscriptionPaymentMethodCreate, 
    SubscriptionPaymentMethodUpdate,
    SubscriptionPayment
)
from app.modules.payments.repositories.subscription_payment_repository import (
    SubscriptionPaymentMethodRepository,
    SubscriptionPaymentRepository
)

router = APIRouter(dependencies=[Depends(get_current_super_admin)])

@router.get("/methods", response_model=List[SubscriptionPaymentMethod])
async def admin_list_methods(db: AsyncSession = Depends(get_db)):
    repo = SubscriptionPaymentMethodRepository(db)
    return await repo.get_all()

@router.post("/methods", response_model=SubscriptionPaymentMethod)
async def admin_create_method(data: SubscriptionPaymentMethodCreate, db: AsyncSession = Depends(get_db)):
    repo = SubscriptionPaymentMethodRepository(db)
    return await repo.create(data.model_dump())

@router.put("/methods/{method_id}", response_model=SubscriptionPaymentMethod)
async def admin_update_method(method_id: int, data: SubscriptionPaymentMethodUpdate, db: AsyncSession = Depends(get_db)):
    repo = SubscriptionPaymentMethodRepository(db)
    method = await repo.get(method_id)
    if not method:
        raise HTTPException(status_code=404, detail="Method not found")
    return await repo.update(method, data.model_dump(exclude_unset=True))

@router.delete("/methods/{method_id}")
async def admin_delete_method(method_id: int, db: AsyncSession = Depends(get_db)):
    repo = SubscriptionPaymentMethodRepository(db)
    method = await repo.get(method_id)
    if not method:
        raise HTTPException(status_code=404, detail="Method not found")
    await repo.remove(method_id)
    return {"success": True}

@router.get("/transactions", response_model=List[SubscriptionPayment])
async def admin_list_transactions(db: AsyncSession = Depends(get_db)):
    repo = SubscriptionPaymentRepository(db)
    return await repo.get_all_with_method()
