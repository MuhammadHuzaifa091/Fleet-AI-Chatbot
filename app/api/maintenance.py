from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.maintenance_service import maintenance_service
from typing import Dict, Any, Optional
from loguru import logger

router = APIRouter()

@router.get("/dashboard")
async def get_maintenance_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get complete maintenance dashboard data"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        return dashboard
    except Exception as e:
        logger.error(f"[MAINTENANCE] Dashboard error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load maintenance dashboard")

@router.get("/upcoming")
async def get_upcoming_maintenance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    maintenance_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("days_until_due"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get paginated upcoming maintenance with filters"""
    filters = {}
    if maintenance_type:
        filters["maintenance_type"] = maintenance_type
    if priority:
        filters["priority"] = priority
    if search:
        filters["search"] = search
    if sort_by:
        filters["sort_by"] = sort_by
    if sort_order:
        filters["sort_order"] = sort_order
    
    try:
        result = await maintenance_service.get_upcoming_maintenance(db, page, page_size, filters)
        return result
    except Exception as e:
        logger.error(f"[MAINTENANCE] Upcoming maintenance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load upcoming maintenance")

@router.get("/overdue")
async def get_overdue_maintenance(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get paginated overdue maintenance"""
    try:
        result = await maintenance_service.get_overdue_maintenance(db, page, page_size)
        return result
    except Exception as e:
        logger.error(f"[MAINTENANCE] Overdue maintenance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load overdue maintenance")

@router.get("/vehicle/{device_id}/status")
async def get_vehicle_maintenance_status(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get maintenance status for a specific vehicle"""
    try:
        status = await maintenance_service.get_vehicle_maintenance_status(db, device_id)
        return status
    except Exception as e:
        logger.error(f"[MAINTENANCE] Vehicle status error for {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load vehicle maintenance status")

@router.get("/activity")
async def get_maintenance_activity(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get recent maintenance activity timeline"""
    try:
        activities = await maintenance_service.get_maintenance_activity(db, limit)
        return {"activities": activities}
    except Exception as e:
        logger.error(f"[MAINTENANCE] Activity error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load maintenance activity")

@router.get("/calendar")
async def get_maintenance_calendar(
    year: int = Query(..., ge=2020, le=2030),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get maintenance calendar for a specific month"""
    try:
        events = await maintenance_service.get_maintenance_calendar(db, year, month)
        return {"events": events, "year": year, "month": month}
    except Exception as e:
        logger.error(f"[MAINTENANCE] Calendar error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load maintenance calendar")

@router.get("/workshops")
async def get_workshops(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all active workshops"""
    try:
        workshops = await maintenance_service.get_workshops(db)
        return {"workshops": workshops}
    except Exception as e:
        logger.error(f"[MAINTENANCE] Workshops error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load workshops")

@router.post("/log")
async def create_maintenance_log(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Record a completed maintenance service"""
    try:
        required = ["device_id", "schedule_id", "service_value"]
        for field in required:
            if field not in payload:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        log = await maintenance_service.create_maintenance_log(
            db=db,
            device_id=payload["device_id"],
            schedule_id=payload["schedule_id"],
            service_value=payload["service_value"],
            service_type=payload.get("service_type", "scheduled"),
            workshop_id=payload.get("workshop_id"),
            technician=payload.get("technician"),
            cost=payload.get("cost", 0),
            notes=payload.get("notes"),
            parts=payload.get("parts"),
            created_by=current_user.get("id")
        )
        return {"id": log.id, "message": "Maintenance log created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MAINTENANCE] Create log error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create maintenance log")

@router.get("/health-summary")
async def get_fleet_health_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get fleet health summary (healthy/warning/critical/unknown counts)"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        return dashboard["fleet_health_summary"]
    except Exception as e:
        logger.error(f"[MAINTENANCE] Health summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load fleet health summary")

@router.get("/kpis")
async def get_maintenance_kpis(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get maintenance KPIs for dashboard cards"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        return dashboard["kpis"]
    except Exception as e:
        logger.error(f"[MAINTENANCE] KPIs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load maintenance KPIs")

@router.get("/charts/maintenance-by-type")
async def get_maintenance_by_type_chart(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get maintenance by type chart data"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        return dashboard["maintenance_by_type"]
    except Exception as e:
        logger.error(f"[MAINTENANCE] Chart error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load maintenance by type chart")

@router.get("/charts/completed-vs-pending")
async def get_completed_vs_pending_chart(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get completed vs pending maintenance chart data"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        kpis = dashboard["kpis"]
        return {
            "completed_today": kpis["completed_today"],
            "pending": kpis["due_today"] + kpis["due_this_week"],
            "overdue": kpis["overdue_maintenance"],
            "active_jobs": kpis["active_workshop_jobs"]
        }
    except Exception as e:
        logger.error(f"[MAINTENANCE] Chart error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load completed vs pending chart")

@router.get("/charts/monthly-trend")
async def get_monthly_trend_chart(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get monthly maintenance trend chart data"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        return {"trend": dashboard["monthly_trend"]}
    except Exception as e:
        logger.error(f"[MAINTENANCE] Monthly trend error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load monthly trend chart")

@router.get("/charts/workshop-workload")
async def get_workshop_workload_chart(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get workshop workload chart data"""
    try:
        dashboard = await maintenance_service.get_fleet_maintenance_dashboard(db)
        return {"workload": dashboard["workshop_workload"]}
    except Exception as e:
        logger.error(f"[MAINTENANCE] Workshop workload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load workshop workload chart")