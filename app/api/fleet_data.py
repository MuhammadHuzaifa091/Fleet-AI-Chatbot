from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.auth import get_current_user
from app.services.fleet_data_service import fleet_data_service
from typing import Dict, Any, Optional

router = APIRouter()


@router.get("/summary")
async def get_fleet_summary(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fleet-wide summary: vehicles, health, costs, inventory"""
    return await fleet_data_service.get_fleet_summary(db)


@router.get("/vehicle/{device_id}")
async def get_vehicle(
    device_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Single vehicle detail with live position"""
    result = await fleet_data_service.get_vehicle(db, device_id)
    if not result:
        raise HTTPException(404, "Vehicle not found")
    return result


@router.get("/vehicles")
async def get_all_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """All vehicles with current positions"""
    return await fleet_data_service.get_all_vehicles(db)


@router.get("/status")
async def get_vehicle_status(
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Vehicle status: online/offline/moving/stopped counts"""
    return await fleet_data_service.get_vehicle_status(db, device_id)


@router.get("/health")
async def get_fleet_health(
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Fleet health scores with breakdown per vehicle"""
    return await fleet_data_service.get_fleet_health(db, device_id)


@router.get("/dashboard")
async def get_fleet_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Unified dashboard: summary + health + recent activity"""
    return await fleet_data_service.get_dashboard(db)


@router.get("/maintenance")
async def get_maintenance_status(
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Maintenance status per vehicle"""
    return await fleet_data_service.get_maintenance_status(db, device_id)


@router.get("/workshop")
async def get_workshop_status(
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Workshop job status per vehicle"""
    return await fleet_data_service.get_workshop_status(db, device_id)


@router.get("/inventory")
async def get_inventory_status(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Inventory summary: stock levels, value, alerts"""
    return await fleet_data_service.get_inventory_status(db)


@router.get("/drivers")
async def get_driver_assignments(
    device_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Driver-to-vehicle assignments"""
    return await fleet_data_service.get_driver_assignment(db, device_id)


@router.get("/history/{device_id}")
async def get_vehicle_history(
    device_id: int,
    days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Full vehicle history: maintenance + workshop + costs"""
    return await fleet_data_service.get_vehicle_history(db, device_id, days)


@router.get("/utilization/{device_id}")
async def get_vehicle_utilization(
    device_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Vehicle utilization: trips, distance, fuel, mileage"""
    return await fleet_data_service.get_vehicle_utilization(db, device_id, days)


@router.get("/costs")
async def get_cost_summary(
    days: int = Query(365, ge=1, le=1095),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cost breakdown: labour, parts, misc, maintenance"""
    return await fleet_data_service.get_cost_summary(db, days)


@router.get("/alerts")
async def get_vehicle_alerts(
    device_id: Optional[int] = Query(None),
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Recent events/alerts per vehicle"""
    return await fleet_data_service.get_vehicle_alerts(db, device_id, days)


@router.post("/cache/invalidate")
async def invalidate_cache(
    pattern: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Invalidate fleet data cache (optionally by pattern)"""
    fleet_data_service.invalidate_all()
    return {"message": "Cache invalidated", "pattern": pattern}
