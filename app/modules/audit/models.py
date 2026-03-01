from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action = Column(String, nullable=False) # e.g., "ACTIVATE_STORE", "BAN_USER"
    target_type = Column(String, nullable=False) # e.g., "store", "user"
    target_id = Column(String, nullable=True)
    changes = Column(JSON, nullable=True) # Old vs New values
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
