import asyncio
from app.services.sync_service import SyncService
import os
from dotenv import load_dotenv

load_dotenv()

async def sync_telemetry():
    print("\n[SYNC] Force fetching Telemetry (Positions/Events) from PC12...")
    from app.services.sync_service import _fetch_telemetry_from_db
    events, positions = await _fetch_telemetry_from_db()
    print(f"[SYNC] Remote fetch done: {len(events)} events, {len(positions)} positions.")
    
    await SyncService._write_telemetry(events, positions)
    print("[SYNC] Telemetry write to local DB complete.")

if __name__ == "__main__":
    asyncio.run(sync_telemetry())
