import base64
import json
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.integrations.models import (
    StoreBeroConnection,
    ProductExternalMapping,
    BeroConnectionStatus,
    BeroOutboxEvent,
    BeroOutboxStatus,
)
from app.modules.integrations.schemas import BeroConnectRequest
from app.modules.products.models import Product, Inventory
from app.modules.orders.models import Order


class BeroIntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _encrypt_token(token: str) -> str:
        return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decrypt_token(value: str) -> str:
        return base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")

    async def _request(self, method: str, path: str, *, token: str | None = None, json_body: dict | None = None):
        headers = {}
        if token:
            headers["X-Company-Token"] = token
            headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(base_url=settings.BERO_BASE_URL.rstrip("/"), timeout=settings.BERO_TIMEOUT_SECONDS) as client:
            return await client.request(method, path, headers=headers, json=json_body)

    async def _verify_company(self, company_identifier: str, company_token: str) -> dict[str, Any]:
        payload = {"identifier": company_identifier}
        response = await self._request("POST", "/companies/verify", token=company_token, json_body=payload)
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Bero verify failed: {response.text}")
        data = response.json()
        if str(data.get("status", "")).lower() != "active":
            raise HTTPException(status_code=400, detail="Company is not active in Bero")
        return data

    async def _get_or_create_connection(self, store_id: int, req: BeroConnectRequest, verify_data: dict[str, Any]) -> StoreBeroConnection:
        result = await self.db.execute(select(StoreBeroConnection).where(StoreBeroConnection.store_id == store_id))
        conn = result.scalar_one_or_none()
        if not conn:
            conn = StoreBeroConnection(store_id=store_id)
            self.db.add(conn)

        conn.company_identifier = req.company_identifier
        conn.company_token_encrypted = self._encrypt_token(req.company_token)
        conn.company_name = verify_data.get("company_name") or verify_data.get("name")
        conn.bero_tenant_id = verify_data.get("id")
        conn.status = BeroConnectionStatus.CONNECTED.value
        conn.is_active = True
        conn.last_verified_at = datetime.now(timezone.utc)
        conn.last_error = None
        return conn

    async def _fetch_bero_products(self, token: str) -> list[dict[str, Any]]:
        response = await self._request("GET", "/products", token=token)
        if response.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"Failed to fetch Bero products: {response.text}")
        data = response.json()
        if isinstance(data, list):
            return data
        return []

    async def _find_local_unlinked_products_count(self, store_id: int) -> int:
        res = await self.db.execute(
            select(func.count(Product.id))
            .select_from(Product)
            .outerjoin(
                ProductExternalMapping,
                and_(
                    ProductExternalMapping.shop_product_id == Product.id,
                    ProductExternalMapping.store_id == Product.store_id,
                    ProductExternalMapping.external_system == "BERO",
                ),
            )
            .where(
                Product.store_id == store_id,
                Product.origin == "LOCAL",
                ProductExternalMapping.id.is_(None),
            )
        )
        return int(res.scalar() or 0)

    async def connect(self, store_id: int, req: BeroConnectRequest) -> dict[str, Any]:
        verify_data = await self._verify_company(req.company_identifier, req.company_token)
        await self._get_or_create_connection(store_id, req, verify_data)

        local_count = await self._find_local_unlinked_products_count(store_id)
        if local_count > 0 and req.resolution_strategy.upper() == "ASK":
            await self.db.commit()
            return {
                "status": "PENDING_DECISION",
                "requires_product_decision": True,
                "local_unlinked_products_count": local_count,
                "message": "Local products exist. Choose CREATE_IN_BERO or DELETE_LOCAL.",
                "company_name": verify_data.get("company_name") or verify_data.get("name"),
            }

        if local_count > 0 and req.resolution_strategy.upper() == "DELETE_LOCAL":
            products = (
                await self.db.execute(
                    select(Product)
                    .outerjoin(
                        ProductExternalMapping,
                        and_(
                            ProductExternalMapping.shop_product_id == Product.id,
                            ProductExternalMapping.store_id == Product.store_id,
                            ProductExternalMapping.external_system == "BERO",
                        ),
                    )
                    .where(
                        Product.store_id == store_id,
                        Product.origin == "LOCAL",
                        ProductExternalMapping.id.is_(None),
                    )
                )
            ).scalars().all()
            for p in products:
                await self.db.delete(p)

        if local_count > 0 and req.resolution_strategy.upper() == "CREATE_IN_BERO":
            local_products = (
                await self.db.execute(
                    select(Product).where(Product.store_id == store_id, Product.origin == "LOCAL")
                )
            ).scalars().all()
            for p in local_products:
                existing_map = await self.db.execute(
                    select(ProductExternalMapping).where(
                        ProductExternalMapping.store_id == store_id,
                        ProductExternalMapping.shop_product_id == p.id,
                        ProductExternalMapping.external_system == "BERO",
                    )
                )
                if existing_map.scalar_one_or_none():
                    continue

                payload = {
                    "name": p.name,
                    "barcode": p.sku or f"SHOP-{store_id}-{p.id}",
                    "retail_price": float(p.price or 0),
                    "primary_quantity": float((p.inventory.quantity if p.inventory else 0) or 0),
                    "secondary_quantity": 0,
                    "conversion_factor": 1,
                }
                resp = await self._request("POST", "/products/", token=req.company_token, json_body=payload)
                if resp.status_code >= 400:
                    continue
                created = resp.json() or {}
                bero_product_id = str(created.get("id") or created.get("product_id") or "")
                if not bero_product_id:
                    continue
                self.db.add(
                    ProductExternalMapping(
                        store_id=store_id,
                        shop_product_id=p.id,
                        external_system="BERO",
                        bero_product_id=bero_product_id,
                        barcode=p.sku,
                        sku=p.sku,
                    )
                )

        synced_count = await self.sync_products(store_id)
        await self.db.commit()
        return {
            "status": "CONNECTED",
            "requires_product_decision": False,
            "local_unlinked_products_count": 0,
            "message": f"Connected and synced {synced_count} products",
            "company_name": verify_data.get("company_name") or verify_data.get("name"),
        }

    async def _upsert_product_from_bero(self, store_id: int, bero_product: dict[str, Any]):
        bero_product_id = str(bero_product.get("id") or "")
        if not bero_product_id:
            return False

        barcode = str(bero_product.get("barcode") or "").strip() or None
        sku = barcode or str(bero_product.get("sku") or "").strip() or None
        quantity = int(float(bero_product.get("primary_quantity") or bero_product.get("quantity") or 0))
        price = float(bero_product.get("retail_price") or bero_product.get("price") or 0)
        name = str(bero_product.get("name") or "Untitled")

        mapping_res = await self.db.execute(
            select(ProductExternalMapping).where(
                ProductExternalMapping.store_id == store_id,
                ProductExternalMapping.external_system == "BERO",
                ProductExternalMapping.bero_product_id == bero_product_id,
            )
        )
        mapping = mapping_res.scalar_one_or_none()

        product = None
        if mapping:
            pres = await self.db.execute(select(Product).where(Product.id == mapping.shop_product_id, Product.store_id == store_id))
            product = pres.scalar_one_or_none()

        if not product and barcode:
            pres = await self.db.execute(select(Product).where(Product.store_id == store_id, Product.sku == barcode))
            product = pres.scalar_one_or_none()

        if not product and sku:
            pres = await self.db.execute(select(Product).where(Product.store_id == store_id, Product.sku == sku))
            product = pres.scalar_one_or_none()

        if not product:
            product = Product(
                store_id=store_id,
                name=name,
                slug=f"bero-{store_id}-{bero_product_id[:12]}",
                description=None,
                price=price,
                sku=sku,
                is_active=True,
                origin="BERO",
            )
            self.db.add(product)
            await self.db.flush()
            self.db.add(Inventory(product_id=product.id, store_id=store_id, quantity=quantity, low_stock_threshold=5))
        else:
            product.name = name
            product.price = price
            product.origin = "BERO"
            if sku:
                product.sku = sku
            inv_res = await self.db.execute(select(Inventory).where(Inventory.product_id == product.id, Inventory.store_id == store_id))
            inv = inv_res.scalar_one_or_none()
            if not inv:
                inv = Inventory(product_id=product.id, store_id=store_id, quantity=quantity, low_stock_threshold=5)
                self.db.add(inv)
            else:
                inv.quantity = quantity

        if not mapping:
            self.db.add(
                ProductExternalMapping(
                    store_id=store_id,
                    shop_product_id=product.id,
                    external_system="BERO",
                    bero_product_id=bero_product_id,
                    barcode=barcode,
                    sku=sku,
                    last_synced_at=datetime.now(timezone.utc),
                )
            )
        else:
            mapping.barcode = barcode
            mapping.sku = sku
            mapping.last_synced_at = datetime.now(timezone.utc)

        return True

    async def sync_products(self, store_id: int) -> int:
        conn_res = await self.db.execute(select(StoreBeroConnection).where(StoreBeroConnection.store_id == store_id, StoreBeroConnection.is_active.is_(True)))
        conn = conn_res.scalar_one_or_none()
        if not conn:
            raise HTTPException(status_code=404, detail="Bero connection not found")

        token = self._decrypt_token(conn.company_token_encrypted)
        products = await self._fetch_bero_products(token)
        synced = 0
        for p in products:
            ok = await self._upsert_product_from_bero(store_id, p)
            if ok:
                synced += 1

        conn.last_sync_at = datetime.now(timezone.utc)
        conn.last_successful_sync_at = datetime.now(timezone.utc)
        conn.last_error = None
        return synced

    async def get_status(self, store_id: int) -> dict[str, Any]:
        conn_res = await self.db.execute(select(StoreBeroConnection).where(StoreBeroConnection.store_id == store_id))
        conn = conn_res.scalar_one_or_none()
        if not conn:
            return {
                "connected": False,
                "status": "DISCONNECTED",
                "mapped_products_count": 0,
            }

        mapped_count = await self.db.execute(
            select(func.count(ProductExternalMapping.id)).where(ProductExternalMapping.store_id == store_id, ProductExternalMapping.external_system == "BERO")
        )
        return {
            "connected": bool(conn.is_active and conn.status == BeroConnectionStatus.CONNECTED.value),
            "status": conn.status,
            "company_name": conn.company_name,
            "company_identifier": conn.company_identifier,
            "bero_tenant_id": conn.bero_tenant_id,
            "last_sync_at": conn.last_sync_at,
            "last_successful_sync_at": conn.last_successful_sync_at,
            "last_error": conn.last_error,
            "mapped_products_count": int(mapped_count.scalar() or 0),
        }

    async def disconnect(self, store_id: int) -> None:
        conn_res = await self.db.execute(select(StoreBeroConnection).where(StoreBeroConnection.store_id == store_id))
        conn = conn_res.scalar_one_or_none()
        if conn:
            conn.is_active = False
            conn.status = BeroConnectionStatus.DISCONNECTED.value
            conn.updated_at = datetime.now(timezone.utc)

    async def enqueue_order_accepted(self, order: Order) -> None:
        if not order:
            return
        conn_res = await self.db.execute(select(StoreBeroConnection).where(StoreBeroConnection.store_id == order.store_id, StoreBeroConnection.is_active.is_(True)))
        conn = conn_res.scalar_one_or_none()
        if not conn:
            return

        existing = await self.db.execute(
            select(BeroOutboxEvent).where(BeroOutboxEvent.order_id == order.id, BeroOutboxEvent.event_type == "ORDER_ACCEPTED")
        )
        if existing.scalar_one_or_none():
            return

        payload = {
            "order_id": order.id,
            "store_id": order.store_id,
            "customer_id": order.customer_id,
            "shipping_address": order.shipping_address,
            "total_amount": float(order.total_amount or 0),
        }
        self.db.add(
            BeroOutboxEvent(
                store_id=order.store_id,
                order_id=order.id,
                event_type="ORDER_ACCEPTED",
                payload_json=json.dumps(payload),
                status=BeroOutboxStatus.PENDING.value,
            )
        )

    async def process_outbox(self) -> int:
        now = datetime.now(timezone.utc)
        rows = await self.db.execute(
            select(BeroOutboxEvent)
            .where(
                BeroOutboxEvent.status.in_([BeroOutboxStatus.PENDING.value, BeroOutboxStatus.FAILED.value]),
                (BeroOutboxEvent.next_retry_at.is_(None) | (BeroOutboxEvent.next_retry_at <= now)),
            )
            .order_by(BeroOutboxEvent.created_at.asc())
            .limit(50)
        )
        events = rows.scalars().all()
        sent = 0

        for ev in events:
            conn_res = await self.db.execute(select(StoreBeroConnection).where(StoreBeroConnection.store_id == ev.store_id, StoreBeroConnection.is_active.is_(True)))
            conn = conn_res.scalar_one_or_none()
            if not conn:
                ev.status = BeroOutboxStatus.FAILED.value
                ev.last_error = "No active Bero connection"
                ev.attempts += 1
                ev.next_retry_at = now + timedelta(minutes=5)
                continue

            token = self._decrypt_token(conn.company_token_encrypted)
            order_res = await self.db.execute(select(Order).where(Order.id == ev.order_id, Order.store_id == ev.store_id))
            order = order_res.scalar_one_or_none()
            if not order:
                ev.status = BeroOutboxStatus.FAILED.value
                ev.last_error = "Order not found"
                ev.attempts += 1
                ev.next_retry_at = now + timedelta(minutes=5)
                continue

            items_res = await self.db.execute(select(ProductExternalMapping, Product, Inventory).join(Product, Product.id == ProductExternalMapping.shop_product_id).join(Inventory, Inventory.product_id == Product.id, isouter=True).where(ProductExternalMapping.store_id == ev.store_id))
            mapping_by_shop = {m.shop_product_id: m for m, _p, _i in items_res.all()}

            full_order = await self.db.execute(select(Order).where(Order.id == order.id))
            order_model = full_order.scalar_one_or_none()
            item_rows = await self.db.execute(select(Order).where(Order.id == order.id))
            _ = item_rows

            order_with_items = await self.db.execute(select(Order).where(Order.id == order.id))
            order_with_items = order_with_items.scalar_one_or_none()
            if not order_with_items:
                continue
            await self.db.refresh(order_with_items, attribute_names=["items"])

            invoice_items = []
            missing_map = False
            for it in order_with_items.items:
                m = mapping_by_shop.get(it.product_id)
                if not m:
                    missing_map = True
                    break
                invoice_items.append(
                    {
                        "product_id": m.bero_product_id,
                        "primary_quantity": float(it.quantity),
                        "secondary_quantity": 0,
                        "unit_price": float(it.unit_price),
                        "total_price": float(it.total_price),
                    }
                )

            if missing_map:
                ev.status = BeroOutboxStatus.FAILED.value
                ev.last_error = "Missing product mapping"
                ev.attempts += 1
                ev.next_retry_at = now + timedelta(minutes=5)
                continue

            payload = {
                "customer_id": None,
                "invoice_number": f"SHOP-{order.id}",
                "total": float(order.total_amount or 0),
                "paid_amount": 0,
                "items": invoice_items,
            }
            resp = await self._request("POST", "/sales", token=token, json_body=payload)
            if resp.status_code >= 400:
                ev.status = BeroOutboxStatus.FAILED.value
                ev.last_error = f"Bero sales failed: {resp.text[:500]}"
                ev.attempts += 1
                ev.next_retry_at = now + timedelta(minutes=min(60, 2 ** min(ev.attempts, 6)))
                continue

            data = resp.json() if resp.content else {}
            ev.status = BeroOutboxStatus.SENT.value
            ev.bero_sales_invoice_id = str(data.get("id") or data.get("invoice_id") or "")
            ev.last_error = None
            ev.attempts += 1
            sent += 1

        return sent
