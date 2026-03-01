from app.core.events import event_dispatcher
from app.modules.notifications.services.notification_service import NotificationService
from app.modules.notifications.repositories.notification_repository import NotificationRepository
from app.core.database import AsyncSessionLocal

async def on_order_status_changed(order, old_status, new_status):
    """Handler for order status changes to notify the customer."""
    async with AsyncSessionLocal() as db:
        repo = NotificationRepository(db)
        service = NotificationService(repo)

        def _status_value(s):
            return getattr(s, "value", str(s))

        status_map = {
            "PENDING": "بانتظار قبول المتجر",
            "ACCEPTED": "تم قبول الطلب",
            "PREPARING": "قيد التحضير",
            "READY": "جاهز للاستلام",
            "OUT_FOR_DELIVERY": "خرج للتوصيل",
            "DELIVERED": "تم التوصيل",
            "CANCELLED": "ملغي",
            "RETURNED": "مرتجع",
        }

        old_val = str(_status_value(old_status)).upper()
        new_val = str(_status_value(new_status)).upper()
        old_ar = status_map.get(old_val, old_val)
        new_ar = status_map.get(new_val, new_val)

        title = f"تحديث حالة الطلب رقم #{order.id}"
        message = f"تم تغيير حالة طلبك من {old_ar} إلى {new_ar}."
        
        await service.notify_user(
            user_id=order.customer_id,
            title=title,
            message=message,
            type="order",
            data={"order_id": order.id, "status": _status_value(new_status)}
        )

def setup_event_handlers():
    """Register all global event listeners."""
    event_dispatcher.subscribe("order_status_changed", on_order_status_changed)
