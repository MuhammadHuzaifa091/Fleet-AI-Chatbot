from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import SessionLocal
from app.services.vin_service import VINService
from loguru import logger
import json

router = APIRouter()

@router.post("/events")
async def handle_traccar_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Unified Webhook for Traccar events.
    Listens for device updates and position updates to capture VIN.
    """
    try:
        payload = await request.json()
        event_type = payload.get("event", {}).get("type") or "unknown"
        
        # Model 1: OBD Automated (Extracted from Position)
        position = payload.get("position")
        if position:
            device_id = position.get("deviceId")
            attributes = position.get("attributes", {})
            vin = attributes.get("vin")
            
            if vin:
                logger.debug(f"[WEBHOOK] OBD VIN detected for device {device_id}: {vin}")
                async with SessionLocal() as db:
                    background_tasks.add_task(VINService.process_vin_change, db, device_id, vin, 'obd')

        # Model 2: Manual Entry (Extracted from Device Update)
        device = payload.get("device")
        if device:
            device_id = device.get("id")
            attributes = device.get("attributes", {})
            vin = attributes.get("vin")
            
            if vin:
                logger.debug(f"[WEBHOOK] Manual VIN detected for device {device_id}: {vin}")
                async with SessionLocal() as db:
                    background_tasks.add_task(VINService.process_vin_change, db, device_id, vin, 'manual')
        return {"status": "success"}
    except Exception as e:
        logger.error(f"[WEBHOOK ERROR] {e}")
        return {"status": "error", "message": str(e)}
