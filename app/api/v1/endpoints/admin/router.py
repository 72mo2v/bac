from fastapi import APIRouter
from app.api.v1.endpoints.admin import users, stores, couriers, audit
from app.modules.subscriptions.routers.admin_router import router as subscription_admin_router
from app.modules.reports.routers.report_router import router as report_router

from app.modules.payments.routers.admin_payment_router import router as admin_payment_router
from app.modules.rbac.routers.rbac_router import router as rbac_router

admin_router = APIRouter()

admin_router.include_router(users.router, prefix="/users", tags=["admin-users"])
admin_router.include_router(stores.router, prefix="/stores", tags=["admin-stores"])
admin_router.include_router(couriers.router, prefix="/couriers", tags=["admin-couriers"])
admin_router.include_router(audit.router, prefix="/audit", tags=["admin-audit"])
admin_router.include_router(subscription_admin_router, prefix="/subscriptions", tags=["admin-subscriptions"])
admin_router.include_router(admin_payment_router, prefix="/payments", tags=["admin-payments"])


admin_router.include_router(rbac_router, prefix="/rbac", tags=["admin-rbac"])
admin_router.include_router(report_router, prefix="/reports", tags=["admin-reports"])

