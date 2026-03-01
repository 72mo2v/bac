from app.core.exceptions import BusinessRuleException, NotFoundException
from app.modules.orders.models import OrderStatus
from app.modules.orders.repositories.order_repository import OrderRepository, OrderHistoryRepository
from app.modules.products.repositories.product_repository import ProductRepository
from app.modules.orders.schemas import OrderCreate, OrderStatusUpdate
from app.infrastructure.qr_generator import generate_qr_code_base64
from app.core.events import event_dispatcher
from typing import Dict, Set
from sqlalchemy import select
from app.modules.stores.models import Store
from app.modules.products.models import Inventory
from app.modules.integrations.bero_service import BeroIntegrationService

class OrderService:
    # State Machine Definition
    # Current State -> Possible Next States
    TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
        OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
        OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
        OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
        OrderStatus.READY: {OrderStatus.OUT_FOR_DELIVERY, OrderStatus.CANCELLED},
        OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED, OrderStatus.RETURNED},
        OrderStatus.DELIVERED: set(), # Terminating state
        OrderStatus.CANCELLED: set(), # Terminating state
        OrderStatus.RETURNED: set(),  # Terminating state
    }

    def __init__(
        self, 
        order_repo: OrderRepository, 
        product_repo: ProductRepository,
        history_repo: OrderHistoryRepository
    ):
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.history_repo = history_repo

    async def create_order(self, order_in: OrderCreate, customer_id: int):
        total_amount = 0.0
        shipping_total = 0.0
        items_to_create = []
        resolved_store_id = None
        
        for item in order_in.items:
            product = await self.product_repo.get(item.product_id)
            if not product or not product.is_active:
                raise BusinessRuleException(f"Product with ID {item.product_id} is not available or does not exist. Please create it first.")

            max_qty_per_order = getattr(product, "max_qty_per_order", None)
            if max_qty_per_order is not None:
                try:
                    max_qty_per_order = int(max_qty_per_order)
                except Exception:
                    max_qty_per_order = None

            if max_qty_per_order is not None and max_qty_per_order > 0 and int(item.quantity) > int(max_qty_per_order):
                raise BusinessRuleException(f"أقصى كمية مسموحة لهذا المنتج في الطلب هي {int(max_qty_per_order)}")

            product_store_id = getattr(product, "store_id", None)
            if product_store_id is None:
                raise BusinessRuleException("Product store is missing")

            if resolved_store_id is None:
                resolved_store_id = int(product_store_id)
            elif int(product_store_id) != int(resolved_store_id):
                raise BusinessRuleException("لا يمكن إنشاء طلب يحتوي على منتجات من أكثر من متجر")

            if int(order_in.store_id) != int(resolved_store_id):
                raise BusinessRuleException("بيانات المتجر غير صحيحة للمنتجات الموجودة في الطلب")
            
            inv_res = await self.order_repo.db.execute(
                select(Inventory)
                .where(
                    Inventory.product_id == int(product.id),
                    Inventory.store_id == int(resolved_store_id),
                )
                .with_for_update()
            )
            inv = inv_res.scalar_one_or_none()
            if not inv:
                raise BusinessRuleException("المنتج غير متوفر حالياً في المخزون")

            available_qty = int(getattr(inv, "quantity", 0) or 0)
            requested_qty = int(item.quantity or 0)
            if requested_qty <= 0:
                raise BusinessRuleException("الكمية المطلوبة غير صحيحة")
            if available_qty < requested_qty:
                raise BusinessRuleException(f"الكمية غير متوفرة للمنتج (المتاح: {available_qty})")

            inv.quantity = available_qty - requested_qty
            self.order_repo.db.add(inv)
            
            unit_price = product.price
            line_total = unit_price * item.quantity
            total_amount += line_total

            is_free_shipping = bool(getattr(product, "is_free_shipping", True))
            per_unit_shipping_fee = float(getattr(product, "shipping_fee", 0) or 0)
            if not is_free_shipping and per_unit_shipping_fee > 0:
                shipping_total += per_unit_shipping_fee * item.quantity
            
            items_to_create.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "unit_price": unit_price,
                "total_price": line_total
            })

        from app.modules.orders.models import OrderItem

        if resolved_store_id is None:
            raise BusinessRuleException("بيانات المتجر غير صحيحة")

        store_row = await self.order_repo.db.execute(select(Store).where(Store.id == int(resolved_store_id)))
        store = store_row.scalar_one_or_none()
        if not store:
            raise BusinessRuleException("المتجر غير موجود")

        min_order_total = getattr(store, "min_order_total", None)
        if min_order_total is not None:
            try:
                min_order_total = float(min_order_total)
            except Exception:
                min_order_total = None

        if min_order_total is not None and min_order_total > 0 and float(total_amount) < float(min_order_total):
            raise BusinessRuleException(f"الحد الأدنى لإجمالي الطلب هو {float(min_order_total):g}")

        order_shipping_fee = getattr(store, "order_shipping_fee", None)
        if order_shipping_fee is not None:
            try:
                order_shipping_fee = float(order_shipping_fee)
            except Exception:
                order_shipping_fee = None

        if order_shipping_fee is not None and order_shipping_fee > 0:
            shipping_total += float(order_shipping_fee)

        order_data = {
            "store_id": int(resolved_store_id) if resolved_store_id is not None else order_in.store_id,
            "customer_id": customer_id,
            "shipping_address": order_in.shipping_address,
            "total_amount": total_amount + shipping_total,
            "status": OrderStatus.PENDING
        }
        
        db_order = self.order_repo.model(**order_data)
        db_order.items = [OrderItem(**item) for item in items_to_create]
        
        self.order_repo.db.add(db_order)
        await self.order_repo.db.flush()
        await self.order_repo.db.refresh(db_order)
        
        return await self.order_repo.get_with_items(db_order.id)

    async def update_status(self, order_id: int, update: OrderStatusUpdate, user_id: int):
        order = await self.order_repo.get_with_items(order_id)
        if not order:
            raise NotFoundException("Order not found")
        
        # State Machine Validation
        if update.new_status not in self.TRANSITIONS.get(order.status, set()):
            raise BusinessRuleException(
                f"Invalid transition from {order.status} to {update.new_status}"
            )
        
        old_status = order.status
        order.status = update.new_status

        if update.new_status == OrderStatus.CANCELLED:
            for item in order.items:
                inv_res = await self.order_repo.db.execute(
                    select(Inventory)
                    .where(
                        Inventory.product_id == int(item.product_id),
                        Inventory.store_id == int(order.store_id),
                    )
                    .with_for_update()
                )
                inv = inv_res.scalar_one_or_none()
                if inv:
                    inv.quantity = int(inv.quantity or 0) + int(item.quantity or 0)
                    self.order_repo.db.add(inv)
                else:
                    self.order_repo.db.add(
                        Inventory(
                            product_id=int(item.product_id),
                            store_id=int(order.store_id),
                            quantity=int(item.quantity or 0),
                            low_stock_threshold=5,
                        )
                    )
        
        # If order is READY, generate QR code for delivery validation
        if update.new_status == OrderStatus.READY:
            validation_data = f"ORDER-{order.id}-{order.store_id}"
            order.delivery_qr_code = generate_qr_code_base64(validation_data)
        
        # Update order
        updated_order = await self.order_repo.update(order, {})
        
        # Log to history
        await self.history_repo.create({
            "order_id": order.id,
            "status_from": old_status,
            "status_to": update.new_status,
            "changed_by_id": user_id,
            "note": update.note
        })
        
        # Dispatch Event
        await event_dispatcher.dispatch(
            "order_status_changed", 
            order=updated_order,
            old_status=old_status,
            new_status=update.new_status
        )

        if update.new_status == OrderStatus.ACCEPTED:
            bero_service = BeroIntegrationService(self.order_repo.db)
            await bero_service.enqueue_order_accepted(updated_order)
        
        return updated_order
    async def get_customer_orders(self, customer_id: int):
        return await self.order_repo.get_multi_by_customer(customer_id)
