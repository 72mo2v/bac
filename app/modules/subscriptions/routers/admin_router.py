from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.subscriptions.schemas import (
    SubscriptionPlanCreate, 
    SubscriptionPlanUpdate,
    SubscriptionPlanInDB, 
    SubscriptionInDB,
    InvoiceInDB
)
from app.modules.subscriptions.services.subscription_service import SubscriptionService
from app.modules.subscriptions.repositories.subscription_repository import (
    SubscriptionRepository,
    InvoiceRepository
)

router = APIRouter()

@router.post("/plans", response_model=SubscriptionPlanInDB)
async def create_plan(
    plan_in: SubscriptionPlanCreate,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    return await service.create_plan(plan_in.model_dump())

@router.get("/plans", response_model=List[SubscriptionPlanInDB])
async def list_plans(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    return await service.get_plans(active_only=active_only)

@router.get("/subscriptions", response_model=List[SubscriptionInDB])
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    from sqlalchemy.orm import joinedload
    from app.modules.subscriptions.models import Subscription
    query = select(Subscription).options(
        joinedload(Subscription.store),
        joinedload(Subscription.plan)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/invoices", response_model=List[InvoiceInDB])
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    from sqlalchemy.orm import joinedload
    from app.modules.subscriptions.models import Invoice, Subscription
    query = select(Invoice).options(
        joinedload(Invoice.subscription).joinedload(Subscription.store)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.put("/plans/{id}", response_model=SubscriptionPlanInDB)
async def update_plan(
    id: int,
    plan_update: SubscriptionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    return await service.update_plan(id, plan_update.model_dump(exclude_unset=True))

@router.delete("/plans/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    id: int,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    try:
        await service.delete_plan(id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None

@router.put("/{id}/status", response_model=SubscriptionInDB)
async def update_subscription_status(
    id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    # Simple status update for admin manual override
    sub = await SubscriptionRepository(db).get(id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    updated = await SubscriptionRepository(db).update(sub, {"status": status})
    await db.commit()
    await db.refresh(updated)
    return updated

@router.put("/invoices/{id}/mark-paid", response_model=InvoiceInDB)
async def mark_invoice_paid(
    id: int,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    try:
        return await service.handle_invoice_payment(id, "MANUAL_BY_ADMIN", "ADMIN_PANEL")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    id: int,
    db: AsyncSession = Depends(get_db),
    admin: Any = Depends(get_current_super_admin)
):
    service = SubscriptionService(db)
    try:
        await service.delete_subscription(id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None
