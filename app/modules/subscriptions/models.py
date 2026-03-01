from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum, DateTime, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class SubscriptionStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

class InvoiceStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_days = Column(Integer, default=30)
    trial_days = Column(Integer, default=7)
    limits = Column(JSON, nullable=True) # {max_products: int, max_orders: int, max_couriers: int}
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subscriptions = relationship("Subscription", back_populates="plan")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), unique=True, index=True)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id"))
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.TRIAL)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    auto_renew = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription")
    store = relationship("Store", back_populates="subscription", foreign_keys=[store_id])

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING)
    payment_method = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    subscription = relationship("Subscription", back_populates="invoices")
