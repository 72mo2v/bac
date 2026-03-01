import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Enum, Text, JSON, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class PaymentMethod(str, enum.Enum):
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"
    BANK_TRANSFER = "BANK_TRANSFER"
    ONLINE_PAYMENT = "ONLINE_PAYMENT"
    WALLET = "WALLET"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    REJECTED = "REJECTED" # For manual bank transfers

class StorePaymentMethod(Base):
    __tablename__ = "store_payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=False)
    method_type = Column(Enum(PaymentMethod), nullable=False)
    is_enabled = Column(Boolean, default=True)
    
    display_name = Column(String(100), nullable=False) # e.g. "Vodafone Cash"
    details = Column(JSON, nullable=True)             # e.g. {"number": "010xxxxxxx"}
    instructions = Column(Text, nullable=True)        # "Please send screenshot to..."
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class OrderPayment(Base):
    __tablename__ = "order_payments" # Renaming to be specific

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    store_payment_method_id = Column(Integer, ForeignKey("store_payment_methods.id"), nullable=True)
    
    amount = Column(Float, nullable=False)
    method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    transaction_reference = Column(String, nullable=True)
    proof_image_url = Column(String, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    store_payment_method = relationship("StorePaymentMethod")
    order = relationship("app.modules.orders.models.Order", foreign_keys=[order_id], viewonly=True)

# --- Subscription Payment Infrastructure ---

class SubscriptionPaymentMethod(Base):
    __tablename__ = "subscription_payment_methods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)      # e.g., "Stripe", "PayPal"
    provider = Column(String(50), unique=True, nullable=False) # e.g., "stripe", "paypal"
    is_enabled = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    config = Column(JSON, nullable=False)           # Stores API keys, secrets
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SubscriptionPayment(Base):
    __tablename__ = "subscription_payments"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=True)
    payment_method_id = Column(Integer, ForeignKey("subscription_payment_methods.id"), nullable=False)
    
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="EGP")
    status = Column(String(20), default="pending")  # pending, success, failed, refunded
    
    transaction_id = Column(String(255), index=True) # Provider's transaction ID
    payment_intent_id = Column(String(255))
    provider_response = Column(JSON, nullable=True)
    
    failure_reason = Column(Text, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    method = relationship("SubscriptionPaymentMethod")

class SubscriptionWebhook(Base):
    __tablename__ = "subscription_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    signature = Column(String(500), nullable=True)
    processed = Column(Boolean, default=False, index=True)
    processing_error = Column(Text, nullable=True)
    payment_id = Column(Integer, ForeignKey("subscription_payments.id", ondelete="CASCADE"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
