from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class CourierLocation(Base):
    __tablename__ = "courier_locations"

    id = Column(Integer, primary_key=True, index=True)
    courier_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), index=True, nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    speed = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


Index("ix_courier_locations_courier_created_at", CourierLocation.courier_user_id, CourierLocation.created_at)

