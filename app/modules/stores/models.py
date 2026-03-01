from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, Enum, Date, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class StoreVerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Contact & Location Info
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    district = Column(String, nullable=True)

    working_hours = Column(String, nullable=True)
    return_policy = Column(Text, nullable=True)

    min_order_total = Column(Float, nullable=True)
    order_shipping_fee = Column(Float, nullable=True)

    # Verification / Onboarding
    verification_status = Column(
        Enum(StoreVerificationStatus, name="storeverificationstatus"),
        default=StoreVerificationStatus.PENDING,
        nullable=True,
        index=True,
    )
    is_verified = Column(Boolean, nullable=True)
    commercial_registration_url = Column(String, nullable=True)
    id_card_url = Column(String, nullable=True)
    store_front_photo_url = Column(String, nullable=True)
    gps_latitude = Column(Float, nullable=True)
    gps_longitude = Column(Float, nullable=True)
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_by = relationship("app.modules.auth.models.User", foreign_keys=[verified_by_id])

    # Subscription Link - One-to-One relationship
    subscription = relationship("Subscription", back_populates="store", uselist=False)


    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class StorePageViewDaily(Base):
    __tablename__ = "store_page_views_daily"
    __table_args__ = (
        UniqueConstraint("store_id", "day", name="uq_store_page_views_daily_store_day"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(Date, nullable=False, index=True)
    visits = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
