from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.middleware import get_store_id
from app.modules.auth.models import User, UserRole, StoreUser
from app.modules.payments.schemas import StorePaymentMethod, StorePaymentMethodCreate, StorePaymentMethodUpdate, Payment
from app.modules.payments.repositories.store_payment_repository import StorePaymentMethodRepository
from app.modules.payments.repositories.payment_repository import PaymentRepository
from app.modules.payments.services.store_payment_service import StorePaymentMethodService
from app.modules.orders.models import Order as OrderModel
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

router = APIRouter()


async def _resolve_store_id(db: AsyncSession, current_user: User) -> int:
    ctx_store_id = get_store_id()
    if ctx_store_id:
        if current_user.role != UserRole.SUPER_ADMIN:
            membership = await db.execute(
                select(func.count(StoreUser.id)).where(
                    StoreUser.user_id == current_user.id,
                    StoreUser.store_id == ctx_store_id,
                )
            )
            if int(membership.scalar() or 0) == 0:
                raise HTTPException(status_code=403, detail="Store access denied")
        return int(ctx_store_id)

    result = await db.execute(
        select(StoreUser.store_id).where(StoreUser.user_id == current_user.id).order_by(StoreUser.store_id.asc())
    )
    store_id = result.scalars().first()
    if not store_id:
        raise HTTPException(status_code=404, detail="No store associated with this user")
    return int(store_id)

async def get_store_payment_service(db: AsyncSession = Depends(get_db)) -> StorePaymentMethodService:
    repo = StorePaymentMethodRepository(db)
    return StorePaymentMethodService(repo)

@router.get("/my-methods", response_model=List[StorePaymentMethod])
async def list_my_methods(
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service)
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
         raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(service.repository.db, current_user)
    return await service.get_methods_for_store(store_id)

@router.post("/my-methods", response_model=StorePaymentMethod)
async def create_my_method(
    method_in: StorePaymentMethodCreate,
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service)
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
         raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(service.repository.db, current_user)
    return await service.create_method(store_id, method_in)

@router.put("/my-methods/{method_id}", response_model=StorePaymentMethod)
async def update_my_method(
    method_id: int,
    method_in: StorePaymentMethodUpdate,
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service)
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
         raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(service.repository.db, current_user)
    return await service.update_method(store_id, method_id, method_in)

@router.delete("/my-methods/{method_id}")
async def delete_my_method(
    method_id: int,
    current_user: User = Depends(get_current_active_user),
    service: StorePaymentMethodService = Depends(get_store_payment_service)
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER]:
         raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(service.repository.db, current_user)
    await service.delete_method(store_id, method_id)
    return {"status": "success"}


@router.get("/transactions", response_model=List[Payment])
async def list_transactions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    store_id = await _resolve_store_id(db, current_user)
    repo = PaymentRepository(db)
    result = await db.execute(
        select(repo.model)
        .options(
            selectinload(repo.model.store_payment_method),
            selectinload(repo.model.order).selectinload(OrderModel.customer),
        )
        .where(repo.model.store_id == store_id)
        .order_by(repo.model.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/transactions/{payment_id}", response_model=Payment)
async def get_transaction(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    store_id = await _resolve_store_id(db, current_user)
    repo = PaymentRepository(db)
    payment = await repo.get_with_method(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if current_user.role != UserRole.SUPER_ADMIN and getattr(payment, "store_id", None) != store_id:
        raise HTTPException(status_code=403, detail="Payment does not belong to your store")

    return payment

@router.get("/public/{store_id}", response_model=List[StorePaymentMethod])
async def list_public_methods(
    store_id: int,
    service: StorePaymentMethodService = Depends(get_store_payment_service)
):
    """List enabled payment methods for customers to choose from during checkout."""
    return await service.get_methods_for_store(store_id, enabled_only=True)
