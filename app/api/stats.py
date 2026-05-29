from fastapi import APIRouter, Depends, Response, HTTPException, BackgroundTasks
from datetime import datetime
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.api.auth import get_current_user, DEMO_ACCOUNTS
from app.services.analytics_service import AnalyticsService
from app.services.report_service import ReportService
from app.retrievers.sql_retriever import SQLRetriever
from typing import Dict, Any

router = APIRouter()

@router.get("/summary")
async def get_stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Return key fleet stats for the dashboard analytics panel."""
    try:
        role = current_user.get("role", "USER")
        user_id = current_user.get("id", 0)

        from app.models.traccar import Device, Position, Event, UserDevice
        from sqlalchemy import select, func
        from datetime import timedelta

        if role == "SUPERADMIN" or role == "ADMIN":
            # Full fleet stats
            total_res = await db.execute(select(func.count(Device.id)).where(Device.disabled == False))
            total = total_res.scalar() or 0

            online_res = await db.execute(select(func.count(Device.id)).where(Device.status == 'online', Device.disabled == False))
            online = online_res.scalar() or 0

            moving_res = await db.execute(
                select(func.count(Device.id))
                .join(Position, Device.positionid == Position.id)
                .where(Device.disabled == False, Position.speed > 1)
            )
            moving = moving_res.scalar() or 0

            overspeed_res = await db.execute(
                select(func.count(Event.id))
                .where(Event.type == 'deviceOverspeed', Event.servertime >= datetime.utcnow() - timedelta(days=1))
            )
            overspeed = overspeed_res.scalar() or 0

        else:
            # Restricted USER — only their assigned devices
            total_res = await db.execute(
                select(func.count(Device.id))
                .join(UserDevice, UserDevice.deviceid == Device.id)
                .where(UserDevice.userid == user_id, Device.disabled == False)
            )
            total = total_res.scalar() or 0

            online_res = await db.execute(
                select(func.count(Device.id))
                .join(UserDevice, UserDevice.deviceid == Device.id)
                .where(UserDevice.userid == user_id, Device.status == 'online', Device.disabled == False)
            )
            online = online_res.scalar() or 0

            moving_res = await db.execute(
                select(func.count(Device.id))
                .join(Position, Device.positionid == Position.id)
                .join(UserDevice, UserDevice.deviceid == Device.id)
                .where(UserDevice.userid == user_id, Device.disabled == False, Position.speed > 1)
            )
            moving = moving_res.scalar() or 0

            overspeed = 0  # Simplified for USER role

        offline = total - online

        return {
            "total_vehicles": int(total),
            "online": int(online),
            "offline": int(offline),
            "moving": int(moving),
            "stationary": int(online - moving),
            "overspeed_today": int(overspeed),
            "role": role
        }

    except Exception as e:
        return {
            "total_vehicles": 0,
            "online": 0,
            "offline": 0,
            "moving": 0,
            "stationary": 0,
            "overspeed_today": 0,
            "error": str(e)
        }

async def generate_report_task(db: AsyncSession, current_user: Dict[str, Any], filename: str):
    try:
        user_id = current_user.get("id")
        role = current_user.get("role")
        
        # 1. Get summary data
        summary = await AnalyticsService.get_analytics_summary(db, user_id, role)
        
        # 2. Get detailed vehicle data
        retriever = SQLRetriever(db, current_user)
        vehicles = await retriever.get_live_vehicles()
        
        # 3. Generate PDF
        ReportService.generate_fleet_report_file(summary, vehicles, filename)
    except Exception as e:
        print(f"Background Report Task Failed: {e}")

@router.post("/report/generate")
async def start_report_generation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Start background report generation."""
    reports_dir = "static/reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        
    filename = f"{reports_dir}/FleetReport_{current_user['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    background_tasks.add_task(generate_report_task, db, current_user, filename)
    
    return {
        "status": "started",
        "message": "Report generation started in background",
        "download_url": f"/{filename}"
    }

@router.get("/report")
async def get_fleet_report(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    # Existing direct download remains for small reports if needed
    try:
        user_id = current_user.get("id")
        role = current_user.get("role")
        summary = await AnalyticsService.get_analytics_summary(db, user_id, role)
        retriever = SQLRetriever(db, current_user)
        vehicles = await retriever.get_live_vehicles()
        pdf_buffer = ReportService.generate_fleet_report(summary, vehicles)
        
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=FleetReport_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report failed: {str(e)}")
