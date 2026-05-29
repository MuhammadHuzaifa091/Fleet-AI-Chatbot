import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def test():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    try:
        async with engine.connect() as conn:
            print("DB Connection: SUCCESS")
    except Exception as e:
        print(f"DB Connection: FAILED - {e}")

if __name__ == "__main__":
    asyncio.run(test())
