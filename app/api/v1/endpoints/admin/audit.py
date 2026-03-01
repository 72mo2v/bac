from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.audit.repositories.audit_repository import AuditRepository
from app.modules.audit.schemas import AuditLog
from app.modules.auth.models import User

router = APIRouter()

@router.get("/", response_model=List[AuditLog])
async def get_audit_logs(
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    current_admin: User = Depends(get_current_super_admin)
) -> Any:

    """Retrieve system audit logs (Super Admin only)."""
    audit_repo = AuditRepository(db)
    return await audit_repo.get_recent_logs(limit=limit)
