import asyncio
import sys
import os
from app.services.sync_service import SyncService, PC12_DB_HOST, PC12_DB_USER, PC12_DB_PASS, PC12_DB_NAME
from app.db.session import SessionLocal
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def check_remote_direct():
    db_url = f"mysql+aiomysql://{PC12_DB_USER}:{PC12_DB_PASS}@{PC12_DB_HOST}/{PC12_DB_NAME}"
    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT COUNT(*) FROM tc_devices"))
            count = res.scalar()
            print(f"DEBUG: Remote PC12 Device Count directly: {count}")
            return count
    except Exception as e:
        print(f"DEBUG: Remote DB Access Error: {e}")
        return None
    finally:
        await engine.dispose()

async def run_manual_sync():
    print("\n" + "="*60)
    print("  MANUAL DATABASE SYNC: PC12 (MASTER) -> PC14 (LOCAL)")
    print("="*60)
    
    remote_count = await check_remote_direct()
    
    async with SessionLocal() as db:
        print("[1/2] Initiating Sync Service...")
        result = await SyncService.sync_from_pc12(db)
        
        if result["status"] == "success":
            print(f"✅ SYNC SUCCESSFUL!")
            print(f"   Mode:         {result['mode']}")
            print(f"   Users:        {result['synced']['users']}")
            print(f"   Devices:      {result['synced']['devices']}")
            print(f"   Permissions:  {result['synced']['permissions']}")
        elif result["status"] == "busy":
            print(f"⚠️  SYNC BUSY: {result['message']}")
        else:
            print(f"❌ SYNC FAILED!")
            for err in result.get("errors", []):
                print(f"   Error: {err}")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(run_manual_sync())
