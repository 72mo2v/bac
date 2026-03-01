from fastapi import APIRouter
from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.stores.routers.store_router import router as store_router
from app.modules.products.routers.product_router import router as product_router
from app.modules.products.routers.cart_router import router as cart_router
from app.modules.orders.routers.order_router import router as order_router
from app.modules.couriers.routers.courier_router import router as courier_router
from app.modules.payments.routers.payment_router import router as payment_router
from app.modules.notifications.routers.notification_router import router as notification_router
from app.modules.subscriptions.routers.store_router import router as subscription_store_router
from app.modules.payments.routers.subscription_payment_router import router as sub_payment_router
from app.modules.payments.routers.webhook_router import router as webhook_router
from app.modules.payments.routers.store_payment_router import router as store_payment_router
from app.modules.support.routers.support_router import router as support_router
from app.api.v1.endpoints.admin.router import admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(store_router, prefix="/stores", tags=["stores"])
api_router.include_router(store_payment_router, prefix="/store-payments", tags=["store-payments"])

api_router.include_router(product_router, prefix="/products", tags=["products"])
api_router.include_router(cart_router, prefix="/cart", tags=["cart"])
api_router.include_router(order_router, prefix="/orders", tags=["orders"])
api_router.include_router(courier_router, prefix="/couriers", tags=["couriers"])
api_router.include_router(payment_router, prefix="/payments", tags=["payments"])
api_router.include_router(notification_router, prefix="/notifications", tags=["notifications"])
api_router.include_router(subscription_store_router, prefix="/subscriptions", tags=["subscriptions"])
api_router.include_router(sub_payment_router, prefix="/payments/subscriptions", tags=["subscription-payments"])
api_router.include_router(webhook_router, prefix="/payments/webhook", tags=["webhooks"])
api_router.include_router(support_router, prefix="/support", tags=["support"])
