from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.traccar import (
    Device, Position, Maintenance as TraccarMaintenance,
    MaintenanceSchedule, VehicleMaintenance, MaintenanceLog,
    Workshop, MaintenanceAlert
)
from app.services.traccar_api_client import get_traccar_client
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
import json


class MaintenanceService:
    """Maintenance management service with all business logic"""
    
    # Maintenance types and their default intervals (km)
    MAINTENANCE_TYPES = {
        "oil_change": {"name": "Oil Change", "default_km": 5000, "default_days": 180, "color": "#3b82f6"},
        "filter_change": {"name": "Filter Change", "default_km": 10000, "default_days": 365, "color": "#10b981"},
        "brake_service": {"name": "Brake Service", "default_km": 20000, "default_days": 730, "color": "#f59e0b"},
        "tire_rotation": {"name": "Tire Rotation", "default_km": 10000, "default_days": 365, "color": "#8b5cf6"},
        "transmission": {"name": "Transmission Service", "default_km": 40000, "default_days": 1460, "color": "#ef4444"},
        "coolant": {"name": "Coolant Flush", "default_km": 50000, "default_days": 1095, "color": "#06b6d4"},
        "spark_plugs": {"name": "Spark Plugs", "default_km": 30000, "default_days": 730, "color": "#f97316"},
        "inspection": {"name": "General Inspection", "default_km": 10000, "default_days": 365, "color": "#6366f1"},
    }
    
    # Priority thresholds
    DUE_SOON_KM = 500      # Within 500 km
    DUE_SOON_DAYS = 14     # Within 14 days
    OVERDUE_KM = 0         # Past due
    CRITICAL_OVERDUE_KM = 1000  # 1000 km overdue
    
    @staticmethod
    async def get_device_current_odometer(db: AsyncSession, device_id: int) -> float:
        """Get current odometer reading for a device from latest position"""
        try:
            # Get from Traccar API (most current)
            traccar = await get_traccar_client()
            positions = await traccar.get_device_positions(device_id)
            if positions:
                pos = positions[0]
                attrs = pos.get("attributes", {}) or {}
                total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
                if total_dist > 0:
                    # Convert from meters to km if needed
                    return round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)
            
            # Fallback to database
            result = await db.execute(
                select(Position.attributes)
                .where(Position.deviceid == device_id)
                .order_by(Position.devicetime.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row and isinstance(row, dict):
                total_dist = row.get("totalDistance") or row.get("odometer") or 0
                if total_dist > 0:
                    return round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)
        except Exception as e:
            logger.warning(f"[MAINTENANCE] Error getting odometer for device {device_id}: {e}")
        return 0.0
    
    @staticmethod
    async def get_all_devices_with_odometer(db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all devices with their current odometer readings"""
        traccar = await get_traccar_client()
        devices = await traccar.get_devices()
        if not devices:
            return []
        
        positions = await traccar.get_positions()
        pos_map = {p.get("deviceId"): p for p in positions} if positions else {}
        
        result = []
        for d in devices:
            device_id = d.get("id")
            pos = pos_map.get(device_id, {})
            attrs = pos.get("attributes", {}) or {}
            total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
            odometer_km = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)
            
            result.append({
                "id": device_id,
                "name": d.get("name", str(device_id)),
                "uniqueId": d.get("uniqueId", ""),
                "status": d.get("status", "unknown"),
                "groupId": d.get("groupId"),
                "odometer_km": odometer_km,
                "lastUpdate": d.get("lastUpdate"),
                "position": pos
            })
        return result
    
    @classmethod
    def _parse_traccar_maintenance(cls, tm: TraccarMaintenance) -> Dict[str, Any]:
        """Parse Traccar maintenance attributes into standard format"""
        attrs = tm.attributes or {}
        # period is in meters, convert to km
        interval_km = round(tm.period / 1000, 2) if tm.period and tm.period > 0 else attrs.get("interval_km", 5000)
        interval_days = attrs.get("interval_days", 180)
        return {
            "id": tm.id,
            "name": tm.name,
            "type": tm.type.lower().replace(" ", "_"),
            "interval_km": interval_km,
            "interval_days": interval_days,
            "description": attrs.get("description", "")
        }
    
    @classmethod
    async def calculate_maintenance_status(
        cls,
        current_km: float,
        schedule: Dict[str, Any],
        vehicle_maint: VehicleMaintenance = None
    ) -> Dict[str, Any]:
        """Calculate maintenance status for a specific schedule on a vehicle"""
        
        # Get schedule parameters
        start_km = 0
        interval_km = schedule.get("interval_km", 0)
        interval_days = schedule.get("interval_days", 0)
        
        # Get last service
        last_service_km = vehicle_maint.last_service_value if vehicle_maint else start_km
        last_service_date = vehicle_maint.last_service_date if vehicle_maint else None
        
        # Calculate base date for the current interval
        if last_service_date:
            base_date = last_service_date
        else:
            # No service history — assume halfway through the current interval
            start_date = datetime.utcnow() - timedelta(days=max(1, interval_days // 2))
            base_date = start_date
        if interval_km > 0:
            # Distance-based: find next multiple
            elapsed_km = current_km - start_km
            if elapsed_km <= 0:
                next_due_km = start_km + interval_km
            else:
                completed_intervals = int(elapsed_km / interval_km)
                next_due_km = start_km + ((completed_intervals + 1) * interval_km)
            km_until_due = next_due_km - current_km
        else:
            next_due_km = None
            km_until_due = None
        
        # Calculate date-based due
        if interval_days > 0 and base_date:
            next_due_date = base_date + timedelta(days=interval_days)
            days_until_due = (next_due_date - datetime.utcnow()).days
        else:
            next_due_date = None
            days_until_due = None
        
        # Determine which comes first (distance or time)
        due_km = next_due_km
        due_date = next_due_date
        primary_metric = "km"
        
        if due_km is not None and due_date is not None:
            # Both exist, use whichever comes first
            # Estimate daily km to compare
            if km_until_due is not None and days_until_due is not None:
                # If we'd reach km due before date due, use km
                estimated_daily_km = 100  # default assumption
                if km_until_due / estimated_daily_km < days_until_due:
                    primary_metric = "km"
                else:
                    primary_metric = "date"
            else:
                primary_metric = "km" if km_until_due is not None else "date"
        elif due_km is not None:
            primary_metric = "km"
        elif due_date is not None:
            primary_metric = "date"
        else:
            primary_metric = "none"
        
        # Determine status
        is_overdue = False
        is_due_soon = False
        days_overdue = 0
        km_overdue = 0
        risk_level = "healthy"
        priority = "low"
        
        if primary_metric == "km" and km_until_due is not None:
            if km_until_due <= cls.OVERDUE_KM:
                is_overdue = True
                km_overdue = abs(km_until_due)
                if km_overdue >= cls.CRITICAL_OVERDUE_KM:
                    risk_level = "critical"
                    priority = "critical"
                else:
                    risk_level = "overdue"
                    priority = "high"
            elif km_until_due <= cls.DUE_SOON_KM:
                is_due_soon = True
                risk_level = "warning"
                priority = "medium"
            else:
                risk_level = "healthy"
                priority = "low"
        elif primary_metric == "date" and days_until_due is not None:
            if days_until_due <= 0:
                is_overdue = True
                days_overdue = abs(days_until_due)
                if days_overdue >= 30:
                    risk_level = "critical"
                    priority = "critical"
                else:
                    risk_level = "overdue"
                    priority = "high"
            elif days_until_due <= cls.DUE_SOON_DAYS:
                is_due_soon = True
                risk_level = "warning"
                priority = "medium"
            else:
                risk_level = "healthy"
                priority = "low"
        else:
            risk_level = "unknown"
            priority = "low"
        
        return {
            "schedule_id": schedule.get("id"),
            "schedule_name": schedule.get("name", "Unknown"),
            "maintenance_type": schedule.get("type", "unknown"),
            "current_km": current_km,
            "last_service_km": last_service_km,
            "last_service_date": last_service_date.isoformat() if last_service_date else None,
            "interval_km": interval_km,
            "interval_days": interval_days,
            "next_due_km": next_due_km,
            "next_due_date": next_due_date.isoformat() if next_due_date else None,
            "km_until_due": km_until_due,
            "days_until_due": days_until_due,
            "primary_metric": primary_metric,
            "is_overdue": is_overdue,
            "is_due_soon": is_due_soon,
            "km_overdue": km_overdue,
            "days_overdue": days_overdue,
            "risk_level": risk_level,
            "priority": priority,
            "status": "overdue" if is_overdue else ("due_soon" if is_due_soon else "ok")
        }
    
    @classmethod
    async def get_vehicle_maintenance_status(
        cls,
        db: AsyncSession,
        device_id: int,
        current_km: float = None
    ) -> Dict[str, Any]:
        """Get complete maintenance status for a vehicle"""
        
        # Get current odometer if not provided
        if current_km is None:
            current_km = await cls.get_device_current_odometer(db, device_id)
        
        # Get Traccar maintenances
        maint_result = await db.execute(select(TraccarMaintenance))
        traccar_maintenances = maint_result.scalars().all()
        
        statuses = []
        for tm in traccar_maintenances:
            schedule = cls._parse_traccar_maintenance(tm)
            status = await cls.calculate_maintenance_status(current_km, schedule, None)
            status["schedule_name"] = tm.name
            statuses.append(status)
        
        # Overall vehicle status
        overdue_count = sum(1 for s in statuses if s["is_overdue"])
        due_soon_count = sum(1 for s in statuses if s["is_due_soon"])
        critical_count = sum(1 for s in statuses if s["risk_level"] == "critical")
        
        if critical_count > 0:
            overall_status = "critical"
        elif overdue_count > 0:
            overall_status = "overdue"
        elif due_soon_count > 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "device_id": device_id,
            "current_km": current_km,
            "overall_status": overall_status,
            "maintenance_items": statuses,
            "summary": {
                "total": len(statuses),
                "overdue": overdue_count,
                "due_soon": due_soon_count,
                "critical": critical_count,
                "healthy": sum(1 for s in statuses if s["risk_level"] == "healthy")
            }
        }
    
    @classmethod
    async def get_fleet_maintenance_dashboard(
        cls,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get fleet-wide maintenance dashboard data - OPTIMIZED"""
        
        # Get all devices with odometer in ONE bulk call
        devices = await cls.get_all_devices_with_odometer(db)
        
        # Get all Traccar maintenances once
        maint_result = await db.execute(select(TraccarMaintenance))
        traccar_maintenances = maint_result.scalars().all()
        
        all_statuses = []
        total_vehicles = len(devices)
        vehicles_under_maintenance = 0
        due_today = 0
        due_this_week = 0
        overdue_count = 0
        active_workshop_jobs = 0
        completed_today = 0
        
        # Parse schedules once
        schedules = [cls._parse_traccar_maintenance(tm) for tm in traccar_maintenances]
        
        for device in devices:
            current_km = device.get("odometer_km", 0)
            
            # Compute status for all schedules for this vehicle
            statuses = []
            for schedule in schedules:
                status = await cls.calculate_maintenance_status(current_km, schedule, None)
                status["schedule_name"] = schedule.get("name", "Unknown")
                statuses.append(status)
            
            # Overall vehicle status
            overdue_count_v = sum(1 for s in statuses if s["is_overdue"])
            due_soon_count = sum(1 for s in statuses if s["is_due_soon"])
            critical_count = sum(1 for s in statuses if s["risk_level"] == "critical")
            
            if critical_count > 0:
                overall_status = "critical"
            elif overdue_count_v > 0:
                overall_status = "overdue"
            elif due_soon_count > 0:
                overall_status = "warning"
            else:
                overall_status = "healthy"
            
            all_statuses.append({
                "device_id": device["id"],
                "vehicle_name": device["name"],
                "vehicle_id": device["uniqueId"],
                "current_km": current_km,
                "overall_status": overall_status,
                "maintenance_items": statuses,
                "summary": {
                    "total": len(statuses),
                    "overdue": overdue_count_v,
                    "due_soon": due_soon_count,
                    "critical": critical_count,
                    "healthy": sum(1 for s in statuses if s["risk_level"] == "healthy")
                }
            })
            
            if overall_status in ["overdue", "critical"]:
                vehicles_under_maintenance += 1
            
            for item in statuses:
                if item["is_overdue"]:
                    overdue_count += 1
                    if item["primary_metric"] == "date" and item["days_overdue"] == 0:
                        due_today += 1
                    elif item["primary_metric"] == "date" and item["days_overdue"] <= 7:
                        due_this_week += 1
                elif item["is_due_soon"]:
                    if item["primary_metric"] == "date" and item["days_until_due"] is not None:
                        if item["days_until_due"] <= 7:
                            due_this_week += 1
        
        # Get active workshop jobs
        try:
            active_jobs = await db.execute(
                select(func.count(MaintenanceLog.id))
                .where(MaintenanceLog.service_type == "in_progress")
            )
            active_workshop_jobs = active_jobs.scalar() or 0
        except:
            active_workshop_jobs = 0
        
        # Get completed today
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            completed = await db.execute(
                select(func.count(MaintenanceLog.id))
                .where(
                    and_(
                        MaintenanceLog.service_date >= today_start,
                        MaintenanceLog.service_type.in_(["scheduled", "unscheduled"])
                    )
                )
            )
            completed_today = completed.scalar() or 0
        except:
            completed_today = 0
        
        # Calculate Fleet Health Score
        if total_vehicles > 0:
            healthy_vehicles = total_vehicles - vehicles_under_maintenance
            health_score = round((healthy_vehicles / total_vehicles) * 100)
        else:
            health_score = 0
        
        # Fleet Health Summary
        health_summary = {
            "healthy": total_vehicles - vehicles_under_maintenance,
            "warning": sum(1 for s in all_statuses if s["overall_status"] == "warning"),
            "critical": sum(1 for s in all_statuses if s["overall_status"] == "critical"),
            "unknown": sum(1 for s in all_statuses if s["overall_status"] == "unknown")
        }
        
        # Maintenance by Type
        type_counts = {}
        for status in all_statuses:
            for item in status["maintenance_items"]:
                mtype = item.get("maintenance_type", "unknown")
                if mtype not in type_counts:
                    type_counts[mtype] = {"total": 0, "overdue": 0, "due_soon": 0, "ok": 0}
                type_counts[mtype]["total"] += 1
                if item["is_overdue"]:
                    type_counts[mtype]["overdue"] += 1
                elif item["is_due_soon"]:
                    type_counts[mtype]["due_soon"] += 1
                else:
                    type_counts[mtype]["ok"] += 1
        
        # Monthly trend (last 6 months)
        monthly_trend = []
        for i in range(6):
            month_start = (datetime.utcnow().replace(day=1) - timedelta(days=32*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            try:
                count = await db.execute(
                    select(func.count(MaintenanceLog.id))
                    .where(
                        and_(
                            MaintenanceLog.service_date >= month_start,
                            MaintenanceLog.service_date <= month_end
                        )
                    )
                )
                monthly_trend.append({
                    "month": month_start.strftime("%b %Y"),
                    "completed": count.scalar() or 0
                })
            except:
                monthly_trend.append({"month": month_start.strftime("%b %Y"), "completed": 0})
        monthly_trend.reverse()
        
        # Workshop workload
        try:
            workshop_stats = await db.execute(
                select(
                    Workshop.name,
                    func.count(MaintenanceLog.id).label("job_count")
                )
                .join(MaintenanceLog, Workshop.id == MaintenanceLog.workshop_id, isouter=True)
                .where(Workshop.is_active == True)
                .group_by(Workshop.id, Workshop.name)
            )
            workshop_workload = [
                {"workshop": row.name, "jobs": row.job_count}
                for row in workshop_stats.all()
            ]
        except:
            workshop_workload = []
        
        return {
            "kpis": {
                "total_vehicles": total_vehicles,
                "vehicles_under_maintenance": vehicles_under_maintenance,
                "due_today": due_today,
                "due_this_week": due_this_week,
                "overdue_maintenance": overdue_count,
                "active_workshop_jobs": active_workshop_jobs,
                "completed_today": completed_today,
                "fleet_health_score": health_score
            },
            "fleet_health_summary": health_summary,
            "maintenance_by_type": type_counts,
            "monthly_trend": monthly_trend,
            "workshop_workload": workshop_workload,
            "vehicle_statuses": all_statuses
        }
    
    @classmethod
    async def get_upcoming_maintenance(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get paginated upcoming maintenance with filters - OPTIMIZED"""
        
        devices = await cls.get_all_devices_with_odometer(db)
        
        # Get Traccar maintenances once
        maint_result = await db.execute(select(TraccarMaintenance))
        traccar_maintenances = maint_result.scalars().all()
        schedules = [cls._parse_traccar_maintenance(tm) for tm in traccar_maintenances]
        
        all_items = []
        for device in devices:
            current_km = device["odometer_km"]
            for schedule in schedules:
                status = await cls.calculate_maintenance_status(current_km, schedule, None)
                if not status["is_overdue"]:  # Only upcoming
                    all_items.append({
                        "vehicle_id": device["id"],
                        "vehicle_name": device["name"],
                        "vehicle_unique_id": device["uniqueId"],
                        "current_km": current_km,
                        "maintenance_type": status["maintenance_type"],
                        "maintenance_name": schedule.get("name", "Unknown"),
                        "due_date": status["next_due_date"],
                        "due_km": status["next_due_km"],
                        "km_until_due": status["km_until_due"],
                        "days_until_due": status["days_until_due"],
                        "priority": status["priority"],
                        "status": status["status"],
                        "assigned_workshop": None
                    })
        
        # Apply filters
        if filters:
            if filters.get("maintenance_type"):
                all_items = [i for i in all_items if i["maintenance_type"] == filters["maintenance_type"]]
            if filters.get("priority"):
                all_items = [i for i in all_items if i["priority"] == filters["priority"]]
            if filters.get("search"):
                search = filters["search"].lower()
                all_items = [i for i in all_items if search in i["vehicle_name"].lower()]
        
        # Sort
        sort_by = filters.get("sort_by", "days_until_due") if filters else "days_until_due"
        sort_order = filters.get("sort_order", "asc") if filters else "asc"
        
        if sort_by == "days_until_due":
            all_items.sort(key=lambda x: x["days_until_due"] or 999999, reverse=(sort_order == "desc"))
        elif sort_by == "km_until_due":
            all_items.sort(key=lambda x: x["km_until_due"] or 999999, reverse=(sort_order == "desc"))
        elif sort_by == "vehicle_name":
            all_items.sort(key=lambda x: x["vehicle_name"], reverse=(sort_order == "desc"))
        
        # Paginate
        total = len(all_items)
        start = (page - 1) * page_size
        end = start + page_size
        items = all_items[start:end]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    @classmethod
    async def get_overdue_maintenance(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Get paginated overdue maintenance - OPTIMIZED"""
        
        devices = await cls.get_all_devices_with_odometer(db)
        
        # Get Traccar maintenances once
        maint_result = await db.execute(select(TraccarMaintenance))
        traccar_maintenances = maint_result.scalars().all()
        schedules = [cls._parse_traccar_maintenance(tm) for tm in traccar_maintenances]
        
        all_items = []
        for device in devices:
            current_km = device["odometer_km"]
            for schedule in schedules:
                status = await cls.calculate_maintenance_status(current_km, schedule, None)
                if status["is_overdue"]:
                    days_overdue = status.get("days_overdue", 0)
                    km_overdue = status.get("km_overdue", 0)
                    
                    # Calculate risk level
                    if status["risk_level"] == "critical":
                        risk = "Critical"
                    elif days_overdue > 30 or km_overdue > 1000:
                        risk = "Critical"
                    elif days_overdue > 14 or km_overdue > 500:
                        risk = "High"
                    elif days_overdue > 7 or km_overdue > 200:
                        risk = "Medium"
                    else:
                        risk = "Low"
                    
                    all_items.append({
                        "vehicle_id": device["id"],
                        "vehicle_name": device["name"],
                        "vehicle_unique_id": device["uniqueId"],
                        "current_km": current_km,
                        "maintenance_type": status["maintenance_type"],
                        "maintenance_name": schedule.get("name", "Unknown"),
                        "due_date": status["next_due_date"],
                        "due_km": status["next_due_km"],
                        "days_overdue": days_overdue,
                        "km_overdue": km_overdue,
                        "priority": status["priority"],
                        "risk_level": risk,
                        "status": "overdue"
                    })
        
        # Sort by risk level and days overdue
        risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        all_items.sort(key=lambda x: (risk_order.get(x["risk_level"], 99), -x["days_overdue"]))
        
        total = len(all_items)
        start = (page - 1) * page_size
        end = start + page_size
        items = all_items[start:end]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    @classmethod
    async def get_maintenance_activity(
        cls,
        db: AsyncSession,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent maintenance activity timeline"""
        
        try:
            result = await db.execute(
                select(MaintenanceLog)
                .options(
                    selectinload(MaintenanceLog.device),
                    selectinload(MaintenanceLog.workshop)
                )
                .order_by(MaintenanceLog.service_date.desc())
                .limit(limit)
            )
            logs = result.scalars().all()
            
            activities = []
            for log in logs:
                activities.append({
                    "date": log.service_date.isoformat() if log.service_date else None,
                    "vehicle": log.device.name if log.device else f"Device {log.device_id}",
                    "activity": f"{log.service_type.replace('_', ' ').title()}: {log.schedule.name if log.schedule else 'Maintenance'}",
                    "performed_by": log.technician or "Unknown",
                    "workshop": log.workshop.name if log.workshop else "N/A",
                    "status": log.service_type,
                    "cost": log.cost,
                    "odometer": log.service_value
                })
            return activities
        except Exception as e:
            logger.warning(f"[MAINTENANCE] Error fetching activity: {e}")
            return []
    
    @classmethod
    async def get_maintenance_calendar(
        cls,
        db: AsyncSession,
        year: int,
        month: int
    ) -> List[Dict[str, Any]]:
        """Get maintenance calendar for a specific month"""
        
        # Get all upcoming maintenance for the month
        devices = await cls.get_all_devices_with_odometer(db)
        
        events = []
        for device in devices:
            status = await cls.get_vehicle_maintenance_status(db, device["id"])
            for item in status["maintenance_items"]:
                if item["next_due_date"]:
                    due_date = datetime.fromisoformat(item["next_due_date"].replace("Z", "+00:00"))
                    if due_date.year == year and due_date.month == month:
                        events.append({
                            "date": due_date.day,
                            "vehicle_id": device["id"],
                            "vehicle_name": device["name"],
                            "maintenance_type": item["maintenance_type"],
                            "maintenance_name": item["schedule_name"],
                            "due_km": item["next_due_km"],
                            "priority": item["priority"],
                            "is_overdue": item["is_overdue"]
                        })
        
        return events
    
    @classmethod
    async def create_maintenance_log(
        cls,
        db: AsyncSession,
        device_id: int,
        schedule_id: int,
        service_value: float,
        service_type: str = "scheduled",
        workshop_id: int = None,
        technician: str = None,
        cost: float = 0,
        notes: str = None,
        parts: List[Dict] = None,
        created_by: int = None
    ) -> MaintenanceLog:
        """Record a completed maintenance service"""
        
        # Get previous odometer
        prev_log_result = await db.execute(
            select(MaintenanceLog.service_value)
            .where(MaintenanceLog.device_id == device_id)
            .order_by(MaintenanceLog.service_date.desc())
            .limit(1)
        )
        previous_odometer = prev_log_result.scalar_one_or_none()
        
        log = MaintenanceLog(
            device_id=device_id,
            schedule_id=schedule_id,
            service_value=service_value,
            service_type=service_type,
            workshop_id=workshop_id,
            technician=technician,
            cost=cost,
            notes=notes,
            parts_replaced=parts,
            previous_odometer=previous_odometer,
            odometer_difference=service_value - previous_odometer if previous_odometer else None,
            created_by=created_by
        )
        
        db.add(log)
        
        # Update vehicle_maintenance last service
        vm_result = await db.execute(
            select(VehicleMaintenance)
            .where(
                and_(
                    VehicleMaintenance.device_id == device_id,
                    VehicleMaintenance.schedule_id == schedule_id
                )
            )
        )
        vm = vm_result.scalar_one_or_none()
        if vm:
            vm.last_service_km = service_value
            vm.last_service_date = datetime.utcnow()
            vm.next_due_km = service_value + (vm.schedule.interval_km if vm.schedule else 0)
            if vm.schedule and vm.schedule.interval_days:
                vm.next_due_date = datetime.utcnow() + timedelta(days=vm.schedule.interval_days)
        
        await db.commit()
        await db.refresh(log)
        return log
    
    @classmethod
    async def get_workshops(cls, db: AsyncSession) -> List[Dict[str, Any]]:
        """Get all active workshops"""
        result = await db.execute(
            select(Workshop).where(Workshop.is_active == True)
        )
        workshops = result.scalars().all()
        return [
            {
                "id": w.id,
                "name": w.name,
                "code": w.code,
                "address": w.address,
                "city": w.city,
                "phone": w.phone,
                "email": w.email,
                "contact_person": w.contact_person,
                "capabilities": w.capabilities or [],
                "rating": w.rating
            }
            for w in workshops
        ]


# Export for API
maintenance_service = MaintenanceService()