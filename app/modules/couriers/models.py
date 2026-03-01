import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class CourierStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"

class Courier(Base):
    __tablename__ = "couriers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    store_id = Column(Integer, index=True, nullable=True) # If courier belongs to a specific store
    courier_code = Column(String, unique=True, index=True, nullable=True)
    
    status = Column(Enum(CourierStatus), default=CourierStatus.PENDING)
    vehicle_type = Column(String)
    license_plate = Column(String)
    is_available = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    # orders = relationship("Order", back_populates="courier") # Handled in Order model
