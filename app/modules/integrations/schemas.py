from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BeroConnectRequest(BaseModel):
    company_identifier: str
    company_token: str
    resolution_strategy: str = "ASK"  # ASK | CREATE_IN_BERO | DELETE_LOCAL


class BeroConnectionStatusResponse(BaseModel):
    connected: bool
    status: str
    company_name: Optional[str] = None
    company_identifier: Optional[str] = None
    bero_tenant_id: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    last_successful_sync_at: Optional[datetime] = None
    last_error: Optional[str] = None
    mapped_products_count: int = 0


class BeroConnectResponse(BaseModel):
    status: str
    requires_product_decision: bool = False
    local_unlinked_products_count: int = 0
    message: str
    company_name: Optional[str] = None


class BeroSyncNowResponse(BaseModel):
    status: str
    synced_products: int
    message: str
