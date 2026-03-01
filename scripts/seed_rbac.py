import asyncio
import os
import sys

# Add the parent directory to sys.path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select
from app.core.config import settings
from app.core.database import Base
from app.modules.rbac.models import Permission, AdminRole, AdminUser
from app.modules.auth.models import User

async def seed_rbac():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. Create Permissions
        permissions_data = [
            # Users
            {"name": "users.view", "display_name": "عرض المستخدمين", "category": "users"},
            {"name": "users.create", "display_name": "إضافة مستخدم", "category": "users"},
            {"name": "users.edit", "display_name": "تعديل مستخدم", "category": "users"},
            {"name": "users.delete", "display_name": "حذف مستخدم", "category": "users"},
            {"name": "users.manage_roles", "display_name": "إدارة أدوار المستخدمين", "category": "users"},
            
            # Stores
            {"name": "stores.view", "display_name": "عرض المتاجر", "category": "stores"},
            {"name": "stores.edit", "display_name": "تعديل المتاجر", "category": "stores"},
            {"name": "stores.approve", "display_name": "اعتماد المتاجر", "category": "stores"},
            
            # Orders
            {"name": "orders.view", "display_name": "عرض الطلبات", "category": "orders"},
            {"name": "orders.manage", "display_name": "إدارة الطلبات", "category": "orders"},
            
            # Support
            {"name": "support.view", "display_name": "عرض تذاكر الدعم", "category": "support"},
            {"name": "support.reply", "display_name": "الرد على تذاكر الدعم", "category": "support"},
            {"name": "support.manage", "display_name": "إدارة تذاكر الدعم", "category": "support"},
            
            # Reports
            {"name": "reports.view", "display_name": "عرض التقارير", "category": "reports"},
            
            # RBAC
            {"name": "rbac.view", "display_name": "عرض الصلاحيات", "category": "rbac"},
            {"name": "rbac.manage_roles", "display_name": "إدارة الأدوار والصلاحيات", "category": "rbac"},
        ]
        
        all_perms = []
        for p_data in permissions_data:
            query = select(Permission).filter(Permission.name == p_data["name"])
            result = await session.execute(query)
            existing = result.scalar_one_or_none()
            
            if not existing:
                perm = Permission(**p_data)
                session.add(perm)
                all_perms.append(perm)
            else:
                all_perms.append(existing)
        
        await session.flush()
        
        # 2. Create/Update SUPER_ADMIN Role
        query = select(AdminRole).options(selectinload(AdminRole.permissions)).filter(AdminRole.name == "SUPER_ADMIN")
        result = await session.execute(query)
        super_role = result.scalar_one_or_none()
        
        if not super_role:
            super_role = AdminRole(
                name="SUPER_ADMIN",
                display_name="مدير عام النظام",
                description="له كافة الصلاحيات على النظام",
                is_system_role=True
            )
            session.add(super_role)
            await session.flush()
            # Re-fetch to ensure the instance is properly initialized with lazy loaders configured
            query = select(AdminRole).options(selectinload(AdminRole.permissions)).filter(AdminRole.name == "SUPER_ADMIN")
            result = await session.execute(query)
            super_role = result.scalar_one_or_none()
        
        # 3. Assign all permissions to SUPER_ADMIN
        # Using a more direct assignment to avoid triggering lazy loads
        super_role.permissions = all_perms
        
        # 4. Link existing Super Admin user to the role
        query = select(User).filter(User.email == "admin@platform.com")
        result = await session.execute(query)
        admin_user_obj = result.scalar_one_or_none()
        
        if admin_user_obj:
            query = select(AdminUser).filter(AdminUser.user_id == admin_user_obj.id)
            result = await session.execute(query)
            existing_admin = result.scalar_one_or_none()
            
            if not existing_admin:
                admin_user = AdminUser(
                    user_id=admin_user_obj.id,
                    role_id=super_role.id,
                    is_active=True
                )
                session.add(admin_user)
        
        await session.commit()
        print("RBAC system seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_rbac())
