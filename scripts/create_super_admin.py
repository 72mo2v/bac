import asyncio
import os
import sys

# Add the parent directory to sys.path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AsyncSessionLocal
from app.modules.auth.models import User, UserRole
from app.modules.rbac.models import AdminUser, AdminRole, Permission # Import to satisfy SQLAlchemy relationship
from app.core import security
from sqlalchemy import select

async def create_super_admin():
    async with AsyncSessionLocal() as session:
        query = select(User).where(User.email == "admin@platform.com")
        result = await session.execute(query)
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print("Super Admin already exists. Updating role and status...")
            existing_admin.role = UserRole.SUPER_ADMIN
            existing_admin.is_active = True
            existing_admin.is_verified = True
            await session.commit()
            return

        admin_user = User(
            email="admin@platform.com",
            hashed_password=security.get_password_hash("admin123"),
            full_name="System Super Admin",
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )
        session.add(admin_user)
        await session.commit()
        print("Super Admin created: admin@platform.com / admin123")

if __name__ == "__main__":
    asyncio.run(create_super_admin())
