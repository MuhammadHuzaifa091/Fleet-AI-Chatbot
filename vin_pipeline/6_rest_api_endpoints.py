import re
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
# from core.db import get_db_pool
from .3_enrichment_service import process_new_vin

router = APIRouter()

async def get_db_pool():
    class DummyPool:
        class DummyConn:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): pass
            async def fetchrow(self, q, *a): return None
            async def fetch(self, q, *a): return []
            async def execute(self, q, *a): pass
        def acquire(self): return self.DummyConn()
    return DummyPool()

class VinUpdatePayload(BaseModel):
    vin: str

def is_valid_vin(vin: str) -> bool:
    if not vin:
        return False
    vin = vin.upper()
    if len(vin) != 17:
        return False
    # Standard international VIN explicitly forbids I, O, Q
    if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
        return False
    return True

@router.patch("/api/devices/{device_id}/vin")
async def manual_vin_entry(device_id: int, payload: VinUpdatePayload, background_tasks: BackgroundTasks):
    """
    Model B: Manual Entry UI Endpoint.
    Writes the VIN manually provided by the user.
    """
    vin = payload.vin.strip().upper()
    
    # 17-character alphanumeric validation without I, O, Q
    if not is_valid_vin(vin):
        raise HTTPException(
            status_code=400, 
            detail="Invalid VIN format. Must be exactly 17 alphanumeric characters, excluding I, O, and Q."
        )
        
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow("SELECT id FROM tc_devices WHERE id = $1", device_id)
        if not record:
            raise HTTPException(status_code=404, detail="Device not found.")
            
    # Trigger Pipeline (Layer 2 & Layer 3 & Layer 5) in background to prevent blocking UI
    background_tasks.add_task(process_new_vin, device_id=device_id, new_vin=vin, source='manual')
    
    return {"status": "success", "message": "VIN update accepted. Manual profile enrichment started."}

@router.get("/api/devices/{device_id}/profile")
async def get_device_profile(device_id: int):
    """
    Retrieves the vehicle profile and automatically triggers fallback logic if data is incomplete.
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow("""
            SELECT vin, manufacturer, model, year, pid_profile, profile_status 
            FROM tc_devices WHERE id = $1
        """, device_id)
        
        if not record:
            raise HTTPException(status_code=404, detail="Device not found.")
            
        vin = record.get('vin')
        make = record.get('manufacturer')
        model = record.get('model')
        
        # Layer 5 Graceful Fallback check
        is_incomplete = not vin or not make or not model
        
        # Default Layer 5 assumptions if real values do not exist
        fallback_tank_size = 50.0
        fallback_avg_consumption = 10.0
        
        parsed_pids = None
        raw_pids = record.get('pid_profile')
        if raw_pids:
            try:
                parsed_pids = json.loads(raw_pids)
            except Exception:
                pass
                
        return {
            "device_id": device_id,
            "vin": vin,
            "manufacturer": make,
            "model": model,
            "year": record.get('year'),
            "profile_status": record.get('profile_status'),
            "is_incomplete": is_incomplete,
            "assumptions": {
                "tank_size_liters": fallback_tank_size,
                "avg_consumption_kml": fallback_avg_consumption
            },
            "obd_pids": parsed_pids
        }
