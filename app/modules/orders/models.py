import enum
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Float, DateTime, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class OrderStatus(str, enum.Enum):
    PENDING = "PENDING"          # Created by customer
    ACCEPTED = "ACCEPTED"        # Accepted by store
    PREPARING = "PREPARING"      # In kitchen/preparation
    READY = "READY"              # Ready for courier pickup
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY" # Courier picked up
    DELIVERED = "DELIVERED"      # Successfully delivered
    CANCELLED = "CANCELLED"      # Cancelled by user or store
    RETURNED = "RETURNED"        # Returned after delivery


class ReturnStatus(str, enum.Enum):
    PENDING = "PENDING"          # Created by customer
    APPROVED = "APPROVED"        # Approved by store/admin
    REJECTED = "REJECTED"        # Rejected by store/admin


class ReturnRequest(Base):
    __tablename__ = "return_requests"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    reason = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    status = Column(Enum(ReturnStatus), default=ReturnStatus.PENDING, index=True)

    reviewed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    order = relationship("Order")
    proof_images = relationship("ReturnProofImage", back_populates="return_request", cascade="all, delete-orphan")


class ReturnProofImage(Base):
    __tablename__ = "return_proof_images"

    id = Column(Integer, primary_key=True, index=True)
    return_request_id = Column(Integer, ForeignKey("return_requests.id", ondelete="CASCADE"), index=True, nullable=False)
    image_url = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    return_request = relationship("ReturnRequest", back_populates="proof_images")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    courier_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True) # Courier is also a User
    
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = Column(Float, nullable=False)
    shipping_address = Column(String, nullable=False)
    
    # Validation for delivery
    delivery_qr_code = Column(String, nullable=True)
    is_paid = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    history = relationship("OrderHistory", back_populates="order", cascade="all, delete-orphan")
    store = relationship("app.modules.stores.models.Store", foreign_keys=[store_id], primaryjoin="Order.store_id == Store.id", viewonly=True)
    customer = relationship("app.modules.auth.models.User", foreign_keys=[customer_id], viewonly=True)

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("app.modules.products.models.Product")

class OrderHistory(Base):
    """Audit log for state machine transitions"""
    __tablename__ = "order_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    status_from = Column(Enum(OrderStatus))
    status_to = Column(Enum(OrderStatus))
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    note = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    order = relationship("Order", back_populates="history")
