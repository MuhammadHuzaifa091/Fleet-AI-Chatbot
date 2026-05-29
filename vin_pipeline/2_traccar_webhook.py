import logging
import re
from fastapi import APIRouter, Request, BackgroundTasks
from .enrichment_service import process_new_vin

logger = logging.getLogger(__name__)

router = APIRouter()

def is_valid_vin(vin: str) -> bool:
    if not vin:
        return False
    vin = vin.upper()
    if len(vin) != 17:
        return False
    # I, O, Q are not allowed in valid VINs
    if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
        return False
    return True

@router.post("/api/traccar/webhook")
async def traccar_obd_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Traccar webhook receiver. Listens for incoming position/event updates.
    Automatically detects OBD VIN and triggers enrichment.
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}
    
    # Traccar can forward an array of devices/events or a single object
    if not isinstance(data, list):
        data = [data]
        
    processed_count = 0
    for item in data:
        # Check standard Traccar attributes mapping
        if "attributes" in item and "deviceId" in item:
            device_id = item["deviceId"]
            attributes = item["attributes"]
            
            # Scan for io256 (standard Teltonika VIN param) or obdVin
            raw_vin = attributes.get("obdVin") or attributes.get("io256")
            
            if raw_vin and isinstance(raw_vin, str):
                raw_vin = raw_vin.strip().upper()
                if is_valid_vin(raw_vin):
                    # Offload to background task to be non-blocking
                    background_tasks.add_task(
                        process_new_vin, 
                        device_id=device_id, 
                        new_vin=raw_vin, 
                        source='obd'
                    )
                    processed_count += 1

    return {"status": "ok", "vins_detected": processed_count}
