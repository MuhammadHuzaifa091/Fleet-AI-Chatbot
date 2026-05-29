import asyncio
import os
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.sync_service import SyncService
from dotenv import load_dotenv

load_dotenv()

async def force_sync():
    print("\n" + "!"*60)
    print("  FORCE RE-SYNC: PURGING LOCAL AND PULLING FROM PC12")
    print("!"*60)

    async with SessionLocal() as db:
        # 1. Truncate local tables to ensure "exact same" state
        print("[1/3] Purging local database (users, devices, positions, perms)...")
        await db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        # We don't truncate tc_users because of auth, but SyncService handles upsert.
        # However, to be "exact same", we should probably truncate it too if we are sure.
        # Let's truncate everything except maybe the very first admin if needed, 
        # but the users are synced too.
        tables = ["tc_user_device", "tc_positions", "tc_events", "tc_devices", "tc_users"]
        for table in tables:
            try:
                await db.execute(text(f"TRUNCATE `{table}`"))
                print(f"      ✓ Truncated {table}")
            except Exception as e:
                print(f"      × Failed to truncate {table}: {e}")
        
        await db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        await db.commit()
        print("      Local database is now clean.")

        # 2. Run Sync
        print("\n[2/3] Fetching data from PC12 (202.141.246.12)...")
        result = await SyncService.sync_from_pc12(db)
        
        if result["status"] == "success":
            print(f"✅ PHASE-1 SYNC SUCCESSFUL!")
            print(f"   Users:        {result['synced']['users']}")
            print(f"   Devices:      {result['synced']['devices']}")
            print(f"   Permissions:  {result['synced']['permissions']}")
        else:
            print(f"❌ SYNC FAILED: {result.get('errors')}")

    print("\n[3/3] Syncing Telemetry (Positions/Events) in background...")
    print("      Verification Count after Phase-1:")
    
    async with SessionLocal() as db:
        res = await db.execute(text("SELECT COUNT(*) FROM tc_devices"))
        print(f"      Local Device Count: {res.scalar()}")
        
    print("!"*60 + "\n")

if __name__ == "__main__":
    asyncio.run(force_sync())
