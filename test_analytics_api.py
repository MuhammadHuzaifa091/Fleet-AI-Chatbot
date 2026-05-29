import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal
from app.services.analytics_service import AnalyticsService

async def test_analytics():
    async with SessionLocal() as db:
        # Simulate SuperAdmin (id=0, role=SUPERADMIN)
        print("Testing analytics for SUPERADMIN...")
        summary = await AnalyticsService.get_analytics_summary(db, user_id=0, role="SUPERADMIN")
        print("Analytics Summary Result:")
        print(summary)
        
        # Simulate a regular USER (id=1, role=USER)
        print("\nTesting analytics for USER (ID=1)...")
        summary_user = await AnalyticsService.get_analytics_summary(db, user_id=1, role="USER")
        print("User Analytics Summary Result:")
        print(summary_user)

if __name__ == "__main__":
    asyncio.run(test_analytics())
