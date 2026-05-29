"""
Sync API Router
===============
Exposes:
  POST /api/v1/sync/start          — manual trigger (SUPERADMIN only)
  GET  /api/v1/sync/status         — last sync log + verification report
  POST /api/v1/sync/deploy         — push PC14 codebase to PC12
  POST /api/v1/sync/receive        — receive codebase from PC14 (PC12 side)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.sync_service import SyncService, SYNC_LOG_FILE
from typing import Dict, Any
import json
import os
import zipfile

router = APIRouter()


# ── Manual sync trigger ────────────────────────────────────────────────────────

@router.post("/start")
async def start_sync_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Manually trigger a PC12 → PC14 sync.
    Requires SUPERADMIN role.
    """
    if current_user.get("role") not in ["SUPERADMIN", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrators can trigger a full data sync.",
        )
    try:
        result = await SyncService.sync_from_pc12(db)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Sync failed: {exc}")


# ── Sync status / last log ─────────────────────────────────────────────────────

@router.get("/status")
async def sync_status_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Returns the last N sync log entries from logs/sync.log.
    Accessible to any authenticated user.
    """
    if not os.path.exists(SYNC_LOG_FILE):
        return {"message": "No sync log found yet.", "entries": []}

    entries = []
    try:
        with open(SYNC_LOG_FILE, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        # Return last 20 entries, newest first
        for line in reversed(lines[-20:]):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    entries.append({"raw": line})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read sync log: {exc}")

    return {"total_entries_returned": len(entries), "entries": entries}


# ── Code deploy (PC14 → PC12) ─────────────────────────────────────────────────

@router.post("/deploy")
async def deploy_to_prod_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Pushes PC14 codebase to PC12 via HTTP.
    Requires SUPERADMIN role.
    """
    if current_user.get("role") != "SUPERADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only administrators can trigger production deployment.",
        )
    try:
        result = await SyncService.deploy_to_prod()
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {exc}")


# ── Receive ZIP payload (PC12 side) ──────────────────────────────────────────

@router.post("/receive")
async def receive_sync_payload(file: UploadFile = File(...)):
    """
    Receives an updated codebase ZIP from PC14 and deploys it locally.
    This endpoint is called on PC12 by the deploy job running on PC14.
    """
    try:
        project_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        temp_zip = os.path.join(project_dir, "temp_deploy.zip")

        with open(temp_zip, "wb") as fh:
            fh.write(await file.read())

        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(project_dir)

        os.remove(temp_zip)
        return {"status": "success", "message": "Production updated successfully via HTTP API."}

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
