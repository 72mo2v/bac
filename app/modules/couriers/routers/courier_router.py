from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_active_user, require_current_store_id
from app.modules.auth.models import User, UserRole, StoreUser
from app.modules.auth.repositories.user_repository import UserRepository
from app.core.security import get_password_hash
from app.modules.couriers.schemas import Courier, CourierCreate, CourierUpdate, CourierAccountCreate
from app.modules.couriers.repositories.courier_repository import CourierRepository
from app.modules.couriers.services.courier_service import CourierService
import uuid

router = APIRouter()

async def get_courier_service(db: AsyncSession = Depends(get_db)) -> CourierService:
    repo = CourierRepository(db)
    return CourierService(repo)

@router.post("", response_model=Courier)
@router.post("/", response_model=Courier)
async def register_courier(
    courier_in: CourierCreate,
    service: CourierService = Depends(get_courier_service),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    result = await service.courier_repo.db.execute(select(User.id).where(User.id == courier_in.user_id))
    user_id = result.scalar_one_or_none()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Force couriers created from merchant context to belong to current store
    payload = courier_in.model_dump()
    if current_user.role != UserRole.SUPER_ADMIN:
        payload["store_id"] = store_id
    courier_in = CourierCreate(**payload)
    created = await service.register_courier(courier_in)
    await service.courier_repo.db.commit()
    return created

@router.post("/create", response_model=Courier)
@router.post("/create/", response_model=Courier)
async def create_courier_account(
    payload: CourierAccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    user_repo = UserRepository(db)
    existing_user = await user_repo.get_by_email(str(payload.email))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this email already exists")

    user_data = {
        "email": str(payload.email),
        "hashed_password": get_password_hash(payload.password),
        "full_name": payload.full_name,
        "phone_number": payload.phone_number,
        "role": UserRole.COURIER,
        "is_active": True,
    }
    user = await user_repo.create(user_data)

    db.add(StoreUser(user_id=user.id, store_id=store_id, role=UserRole.COURIER))
    await db.flush()

    courier_repo = CourierRepository(db)

    courier_code = None
    for _ in range(5):
        candidate = f"CR-{store_id}-{uuid.uuid4().hex[:10].upper()}"
        exists = await db.execute(select(courier_repo.model.id).where(courier_repo.model.courier_code == candidate))
        if not exists.scalar_one_or_none():
            courier_code = candidate
            break

    if not courier_code:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate courier code")

    courier_in = {
        "user_id": user.id,
        "store_id": store_id,
        "vehicle_type": payload.vehicle_type,
        "license_plate": payload.license_plate,
        "courier_code": courier_code,
    }
    courier = await courier_repo.create(courier_in)
    await db.commit()
    return await courier_repo.get(courier.id)

@router.get("", response_model=List[Courier])
@router.get("/", response_model=List[Courier])
async def list_couriers(
    available_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    repo = CourierRepository(db)
    if available_only:
        return await repo.get_available(store_id=store_id if current_user.role != UserRole.SUPER_ADMIN else None)
    return await repo.get_multi()

@router.patch("/{courier_id}", response_model=Courier)
async def update_courier(
    courier_id: int,
    update: CourierUpdate,
    db: AsyncSession = Depends(get_db),
    service: CourierService = Depends(get_courier_service),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    repo = CourierRepository(db)
    courier = await repo.get(courier_id)
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    if current_user.role != UserRole.SUPER_ADMIN and getattr(courier, "store_id", None) != store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Courier does not belong to your store")

    updated = await service.update_status(courier_id, update)
    await db.commit()
    return updated

@router.delete("/{courier_id}")
async def delete_courier(
    courier_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    store_id: int = Depends(require_current_store_id),
):
    if current_user.role not in [UserRole.SUPER_ADMIN, UserRole.STORE_OWNER, UserRole.STORE_ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    repo = CourierRepository(db)
    courier = await repo.get(courier_id)
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    if current_user.role != UserRole.SUPER_ADMIN and getattr(courier, "store_id", None) != store_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Courier does not belong to your store")

    await repo.remove(courier_id)
    await db.commit()
    return {"status": "success"}
