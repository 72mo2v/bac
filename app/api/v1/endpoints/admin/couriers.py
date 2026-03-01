from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.couriers.schemas import Courier, CourierUpdate

from app.modules.couriers.repositories.courier_repository import CourierRepository
from app.modules.audit.repositories.audit_repository import AuditRepository
from app.modules.auth.models import User

router = APIRouter()

@router.get("/", response_model=List[Courier])
async def list_couriers(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """List all couriers with optional filtering (Super Admin only)."""
    courier_repo = CourierRepository(db)
    # courier_repo inherits get_multi from BaseRepository
    couriers = await courier_repo.get_multi(skip=skip, limit=limit)
    if status:
        couriers = [c for c in couriers if c.status == status]
    return couriers

@router.put("/{courier_id}/status")
async def update_courier_status(
    courier_id: int,
    status: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Update courier status (Super Admin only)."""
    courier_repo = CourierRepository(db)
    audit_repo = AuditRepository(db)
    
    courier = await courier_repo.get(courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    old_status = courier.status
    courier.status = status
    await db.commit()
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="UPDATE_COURIER_STATUS",
        target_type="courier",
        target_id=str(courier_id),
        changes={"status": {"old": old_status, "new": status}},
        ip_address=request.client.host
    )
    
    return {"message": f"Courier status updated to {status}"}

@router.put("/{courier_id}", response_model=Courier)
async def update_courier(
    courier_id: int,
    courier_in: CourierUpdate,

    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Update courier details (Super Admin only)."""
    courier_repo = CourierRepository(db)
    audit_repo = AuditRepository(db)
    
    courier = await courier_repo.get(courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    
    updated_courier = await courier_repo.update(db_obj=courier, obj_in=courier_in.model_dump(exclude_unset=True))
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="UPDATE_COURIER_DETAILS",
        target_type="courier",
        target_id=str(courier_id),
        changes={"name": courier.user.full_name if courier.user else "Unknown", "vehicle": courier_in.vehicle_type},

        ip_address=request.client.host
    )
    
    return updated_courier

@router.delete("/{courier_id}")
async def delete_courier(
    courier_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Delete a courier permanently (Super Admin only)."""
    courier_repo = CourierRepository(db)
    audit_repo = AuditRepository(db)
    
    courier = await courier_repo.get(courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
        
    await courier_repo.remove(id=courier_id)
    
    # Log the action
    await audit_repo.log_action(
        admin_id=current_admin.id,
        action="DELETE_COURIER",
        target_type="courier",
        target_id=str(courier_id),
        changes={"deleted": courier.user.full_name if courier.user else str(courier_id)},
        ip_address=request.client.host
    )
    
    return {"message": "Courier deleted successfully"}

