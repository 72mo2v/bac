import asyncio
import os
import sys

# Add the parent directory to sys.path to import app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

async def list_tables():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result.all()]
        print("Tables in database:")
        for table in sorted(tables):
            print(f" - {table}")

if __name__ == "__main__":
    asyncio.run(list_tables())
