import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class BeroConnectionStatus(str, enum.Enum):
    PENDING_VERIFY = "PENDING_VERIFY"
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class ProductOrigin(str, enum.Enum):
    LOCAL = "LOCAL"
    BERO = "BERO"


class BeroOutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class BeroSyncJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class StoreBeroConnection(Base):
    __tablename__ = "store_bero_connections"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    company_identifier = Column(String, nullable=False)
    company_token_encrypted = Column(Text, nullable=False)
    bero_tenant_id = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    status = Column(String, default=BeroConnectionStatus.PENDING_VERIFY.value, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ProductExternalMapping(Base):
    __tablename__ = "product_external_mappings"
    __table_args__ = (
        UniqueConstraint("store_id", "external_system", "bero_product_id", name="uq_store_external_bero_product"),
        UniqueConstraint("store_id", "shop_product_id", "external_system", name="uq_store_shop_product_external"),
    )

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    shop_product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    external_system = Column(String, nullable=False, default="BERO")
    bero_product_id = Column(String, nullable=False, index=True)
    barcode = Column(String, nullable=True, index=True)
    sku = Column(String, nullable=True, index=True)
    sync_enabled = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BeroSyncJob(Base):
    __tablename__ = "bero_sync_jobs"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default=BeroSyncJobStatus.PENDING.value, index=True)
    cursor = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BeroOutboxEvent(Base):
    __tablename__ = "bero_outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False, default="ORDER_ACCEPTED")
    payload_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, default=BeroOutboxStatus.PENDING.value, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    bero_sales_invoice_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
