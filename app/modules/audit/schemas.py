from typing import Optional, Any
from pydantic import BaseModel
from datetime import datetime

class AuditLogBase(BaseModel):
    admin_id: int
    action: str
    target_type: str
    target_id: Optional[str] = None
    changes: Optional[Any] = None
    ip_address: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
