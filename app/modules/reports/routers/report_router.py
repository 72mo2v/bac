from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_super_admin
from app.modules.reports.services.report_service import ReportService
from app.modules.auth.models import User

router = APIRouter()

@router.get("/summary")
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_super_admin)
) -> Any:
    """Get aggregated summary for Super Admin dashboard."""
    report_service = ReportService(db)
    return await report_service.get_admin_dashboard_summary()
