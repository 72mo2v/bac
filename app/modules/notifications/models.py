from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    store_id = Column(Integer, index=True, nullable=True)
    type = Column(String(50), nullable=True)
    
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSON, nullable=True) # For extra payload like order_id
    
    is_read = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
