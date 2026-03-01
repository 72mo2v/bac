from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.middleware import get_store_id
from app.modules.subscriptions.schemas import (
    SubscriptionInDB,
    InvoiceInDB,
    SubscriptionPlanInDB
)
from app.modules.subscriptions.services.subscription_service import SubscriptionService
from app.modules.auth.models import User, StoreUser, UserRole
from sqlalchemy import select, func

router = APIRouter()


async def _resolve_store_id(db: AsyncSession, user: User) -> int:
    ctx_store_id = get_store_id()
    if ctx_store_id:
        if user.role != UserRole.SUPER_ADMIN:
            membership = await db.execute(
                select(func.count(StoreUser.id)).where(
                    StoreUser.user_id == user.id,
                    StoreUser.store_id == ctx_store_id,
                )
            )
            if int(membership.scalar() or 0) == 0:
                raise HTTPException(status_code=403, detail="Store access denied")
        return int(ctx_store_id)

    result = await db.execute(
        select(StoreUser.store_id).where(StoreUser.user_id == user.id).order_by(StoreUser.store_id.asc())
    )
    store_id = result.scalar_one_or_none()
    if not store_id:
        raise HTTPException(status_code=404, detail="No store associated with this user")
    return int(store_id)

@router.get("/current", response_model=SubscriptionInDB)
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    store_id = await _resolve_store_id(db, user)
    
    service = SubscriptionService(db)
    sub = await service.get_by_store_id(store_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No subscription found for this store")
    return sub

@router.post("/start-trial", response_model=SubscriptionInDB)
async def start_trial(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    store_id = await _resolve_store_id(db, user)
    
    service = SubscriptionService(db)
    try:
        return await service.start_trial(store_id, plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/plans", response_model=List[SubscriptionPlanInDB])
async def list_plans(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    if user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    service = SubscriptionService(db)
    return await service.get_plans(active_only=True)

@router.get("/invoices", response_model=List[InvoiceInDB])
async def list_my_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    store_id = await _resolve_store_id(db, user)
    service = SubscriptionService(db)
    from sqlalchemy import select
    from app.modules.subscriptions.models import Invoice, Subscription
    result = await db.execute(
        select(Invoice)
        .join(Subscription, Subscription.id == Invoice.subscription_id)
        .where(Subscription.store_id == store_id)
        .order_by(Invoice.created_at.desc())
    )
    return result.scalars().all()

@router.post("/upgrade", response_model=SubscriptionInDB)
async def upgrade_subscription(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user)
):
    store_id = await _resolve_store_id(db, user)
    service = SubscriptionService(db)
    subscription = await service.get_by_store_id(store_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found for this store")
    try:
        return await service.upgrade_subscription(subscription.id, plan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
