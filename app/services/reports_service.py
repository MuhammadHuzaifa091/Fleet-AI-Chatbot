from sqlalchemy import select, func, and_, or_, desc, case, literal_column, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.traccar import (
    Device, WorkshopJob, Technician, JobNote, MaintenanceLog, Workshop,
    MaintenanceType, MaintenanceTemplate, SparePart, StockMovement,
    VehicleMaintenance, MaintenanceSchedule
)
from app.services.fleet_data_service import fleet_data_service
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import calendar


class ReportsService:
    """Enterprise Reports & Analytics — consumes FleetDataService as single source of truth"""

    # ==================== REPORT DASHBOARD KPIs ====================

    @staticmethod
    async def get_dashboard_kpis(db: AsyncSession) -> Dict[str, Any]:
        try:
            fleet_summary = await fleet_data_service.get_fleet_summary(db)
            fleet_dashboard = await fleet_data_service.get_dashboard(db)

            now = datetime.utcnow()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_maint_cost = float((await db.execute(
                select(func.sum(MaintenanceLog.cost)).where(
                    and_(MaintenanceLog.service_date >= month_start, MaintenanceLog.cost > 0)
                )
            )).scalar() or 0)

            total_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob))).scalar() or 0
            completed_jobs = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(WorkshopJob.status == "completed")
            )).scalar() or 0
            pending_jobs = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(WorkshopJob.status == "pending")
            )).scalar() or 0

            parts_consumed = float((await db.execute(
                select(func.sum(func.abs(StockMovement.quantity))).where(
                    and_(StockMovement.movement_type == "stock_out",
                         StockMovement.reference_type == "workshop_job")
                )
            )).scalar() or 0)

            avg_repair = float((await db.execute(
                select(func.avg(WorkshopJob.labour_hours)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.labour_hours > 0)
                )
            )).scalar() or 0)

            top_vehicle = None
            top_result = await db.execute(
                select(MaintenanceLog.device_id, func.count().label("cnt"), func.sum(MaintenanceLog.cost).label("total_cost"))
                .group_by(MaintenanceLog.device_id).order_by(desc("cnt")).limit(1)
            )
            top_row = top_result.first()
            if top_row:
                dev = (await db.execute(select(Device).where(Device.id == top_row[0]))).scalar_one_or_none()
                top_vehicle = {"device_id": top_row[0], "name": dev.name if dev else f"Vehicle {top_row[0]}",
                               "service_count": top_row[1], "total_cost": round(float(top_row[2] or 0), 2)}

            return {
                "total_maintenance_cost": fleet_summary.get("total_maintenance_cost", 0),
                "monthly_maintenance_cost": round(monthly_maint_cost, 2),
                "total_workshop_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "pending_jobs": pending_jobs,
                "overdue_vehicles": fleet_dashboard.get("health", {}).get("overdue_maintenances", 0),
                "fleet_health_score": fleet_summary.get("fleet_health_avg", 0),
                "total_spare_parts_value": fleet_summary.get("inventory_value", 0),
                "parts_consumed": round(parts_consumed, 2),
                "inventory_value": fleet_summary.get("inventory_value", 0),
                "top_maintenance_vehicle": top_vehicle,
                "average_repair_time_hours": round(avg_repair, 1),
            }
        except Exception as e:
            logger.warning(f"Error in report dashboard KPIs: {e}")
            return {}

    # ==================== FLEET MAINTENANCE REPORT ====================

    @staticmethod
    async def get_fleet_maintenance_report(db: AsyncSession, days: int = 90) -> Dict[str, Any]:
        try:
            items = await fleet_data_service.get_maintenance_logs(db, days)
            total_cost = sum(i["cost"] or 0 for i in items)
            by_type = {}
            for i in items:
                t = i["service_type"] or "unknown"
                by_type[t] = by_type.get(t, 0) + 1
            by_month = {}
            for i in items:
                if i["service_date"]:
                    m = i["service_date"][:7]
                    by_month[m] = by_month.get(m, 0) + 1

            return {"items": items, "total": len(items), "total_cost": round(total_cost, 2),
                    "by_type": by_type, "by_month": by_month, "days": days}
        except Exception as e:
            logger.warning(f"Error in fleet maintenance report: {e}")
            return {"items": [], "total": 0, "total_cost": 0, "by_type": {}, "by_month": {}, "days": days}

    # ==================== VEHICLE HISTORY REPORT ====================

    @staticmethod
    async def get_vehicle_history(db: AsyncSession, device_id: int) -> Dict[str, Any]:
        try:
            full = await fleet_data_service.get_vehicle_history(db, device_id, days=365)
            return {
                "device_id": device_id,
                "device_name": full.get("vehicle", {}).get("name", f"Vehicle {device_id}"),
                "maintenance_history": full.get("maintenance_history", []),
                "workshop_jobs": full.get("workshop_jobs", []),
                "total_maintenance_cost": full.get("total_maintenance_cost", 0),
                "total_services": len(full.get("maintenance_history", [])),
                "total_jobs": len(full.get("workshop_jobs", [])),
            }
        except Exception as e:
            logger.warning(f"Error in vehicle history: {e}")
            return {"device_id": device_id, "device_name": f"Vehicle {device_id}",
                    "maintenance_history": [], "workshop_jobs": [], "total_maintenance_cost": 0,
                    "total_services": 0, "total_jobs": 0}

    # ==================== WORKSHOP PERFORMANCE ====================

    @staticmethod
    async def get_workshop_performance(db: AsyncSession, days: int = 90) -> Dict[str, Any]:
        try:
            since = datetime.utcnow() - timedelta(days=days)

            total = (await db.execute(select(func.count()).select_from(WorkshopJob))).scalar() or 0
            completed = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.completed_date >= since)
                )
            )).scalar() or 0
            in_progress = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(
                    WorkshopJob.status.in_(["in_progress", "vehicle_arrived", "inspection", "paused", "waiting_parts"])
                )
            )).scalar() or 0
            cancelled = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(WorkshopJob.status == "cancelled")
            )).scalar() or 0

            avg_hours = float((await db.execute(
                select(func.avg(WorkshopJob.labour_hours)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.labour_hours > 0)
                )
            )).scalar() or 0)

            total_cost = float((await db.execute(
                select(func.sum(WorkshopJob.total_cost)).where(WorkshopJob.status == "completed")
            )).scalar() or 0)

            avg_cost = total_cost / completed if completed > 0 else 0

            # Status breakdown
            status_counts = {}
            for s in ["pending", "assigned", "vehicle_arrived", "inspection", "in_progress",
                       "waiting_parts", "paused", "quality_check", "approved", "completed", "cancelled"]:
                cnt = (await db.execute(
                    select(func.count()).select_from(WorkshopJob).where(WorkshopJob.status == s)
                )).scalar() or 0
                status_counts[s] = cnt

            # Monthly trend
            monthly = await db.execute(
                select(func.strftime("%Y-%m", WorkshopJob.created_date).label("month"),
                       func.count().label("cnt"))
                .group_by("month").order_by("month").limit(12)
            )
            trend = [{"month": r[0], "count": r[1]} for r in monthly.all()]

            return {
                "total_jobs": total, "completed": completed, "in_progress": in_progress,
                "cancelled": cancelled, "avg_repair_hours": round(avg_hours, 1),
                "total_cost": round(total_cost, 2), "avg_cost": round(avg_cost, 2),
                "status_counts": status_counts, "monthly_trend": trend, "days": days,
            }
        except Exception as e:
            logger.warning(f"Error in workshop performance: {e}")
            return {}

    # ==================== TECHNICIAN PERFORMANCE ====================

    @staticmethod
    async def get_technician_performance(db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            techs = await db.execute(select(Technician).where(Technician.is_active == True))
            results = []
            for tech in techs.scalars().all():
                completed = (await db.execute(
                    select(func.count()).select_from(WorkshopJob).where(
                        and_(WorkshopJob.technician_id == tech.id, WorkshopJob.status == "completed")
                    )
                )).scalar() or 0

                total_hours = float((await db.execute(
                    select(func.avg(WorkshopJob.labour_hours)).where(
                        and_(WorkshopJob.technician_id == tech.id,
                             WorkshopJob.status == "completed", WorkshopJob.labour_hours > 0)
                    )
                )).scalar() or 0)

                avg_hours = total_hours if completed > 0 else 0

                total_cost = float((await db.execute(
                    select(func.sum(WorkshopJob.total_cost)).where(
                        and_(WorkshopJob.technician_id == tech.id, WorkshopJob.status == "completed")
                    )
                )).scalar() or 0)

                approved = (await db.execute(
                    select(func.count()).select_from(WorkshopJob).where(
                        and_(WorkshopJob.technician_id == tech.id, WorkshopJob.approved == True)
                    )
                )).scalar() or 0

                active = (await db.execute(
                    select(func.count()).select_from(WorkshopJob).where(
                        and_(WorkshopJob.technician_id == tech.id,
                             WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection",
                                                     "in_progress", "waiting_parts", "paused", "quality_check"]))
                    )
                )).scalar() or 0

                approval_rate = round((approved / completed * 100) if completed > 0 else 0, 1)

                results.append({
                    "id": tech.id, "name": tech.name, "employee_id": tech.employee_id,
                    "completed_jobs": completed, "avg_completion_hours": round(avg_hours, 1),
                    "total_cost": round(total_cost, 2),
                    "approval_rate": approval_rate, "active_jobs": active,
                    "max_workload": tech.max_workload or 3,
                })

            results.sort(key=lambda x: x["completed_jobs"], reverse=True)
            return results
        except Exception as e:
            logger.warning(f"Error in technician performance: {e}")
            return []

    # ==================== INVENTORY ANALYTICS ====================

    @staticmethod
    async def get_inventory_analytics(db: AsyncSession) -> Dict[str, Any]:
        try:
            # Most used parts (by stock_out count for workshop_job)
            most_used = await db.execute(
                select(StockMovement.spare_part_id, func.count().label("usage_count"),
                       func.sum(func.abs(StockMovement.quantity)).label("total_qty"),
                       func.sum(StockMovement.total_cost).label("total_cost"))
                .where(and_(StockMovement.movement_type == "stock_out",
                            StockMovement.reference_type == "workshop_job"))
                .group_by(StockMovement.spare_part_id)
                .order_by(desc("usage_count")).limit(10)
            )
            most_used_list = []
            for row in most_used.all():
                part = (await db.execute(select(SparePart).where(SparePart.id == row.spare_part_id))).scalar_one_or_none()
                most_used_list.append({
                    "part_id": row.spare_part_id,
                    "part_name": part.name if part else f"Part {row.spare_part_id}",
                    "part_number": part.part_number if part else "-",
                    "usage_count": row.usage_count,
                    "total_qty": round(float(row.total_qty or 0), 2),
                    "total_cost": round(float(row.total_cost or 0), 2),
                })

            # Least used parts (have stock but never consumed)
            all_parts = await db.execute(
                select(SparePart).where(and_(SparePart.is_active == True, SparePart.current_quantity > 0))
            )
            used_part_ids_result = await db.execute(
                select(StockMovement.spare_part_id).where(
                    and_(StockMovement.movement_type == "stock_out",
                         StockMovement.reference_type == "workshop_job")
                ).distinct()
            )
            used_ids = set(r[0] for r in used_part_ids_result.all())
            least_used = []
            for p in all_parts.scalars().all():
                if p.id not in used_ids:
                    least_used.append({
                        "part_id": p.id, "part_name": p.name, "part_number": p.part_number,
                        "current_stock": p.current_quantity, "unit_cost": p.unit_cost,
                    })

            # Stock aging (parts with oldest last movement)
            aging = await db.execute(
                select(SparePart.id, SparePart.name, SparePart.part_number,
                       SparePart.current_quantity, SparePart.unit_cost,
                       func.max(StockMovement.created_at).label("last_movement"))
                .outerjoin(StockMovement, SparePart.id == StockMovement.spare_part_id)
                .where(SparePart.is_active == True)
                .group_by(SparePart.id)
                .order_by(StockMovement.created_at.asc().nullslast()).limit(10)
            )
            aging_list = []
            for row in aging.all():
                days_old = (datetime.utcnow() - row[5]).days if row[5] else None
                aging_list.append({
                    "part_id": row[0], "part_name": row[1], "part_number": row[2],
                    "current_stock": row[3], "unit_cost": row[4],
                    "last_movement": row[5].isoformat() if row[5] else None,
                    "days_since_movement": days_old,
                })

            # Category breakdown
            cat_result = await db.execute(
                select(SparePart.category, func.count().label("cnt"),
                       func.sum(SparePart.current_quantity * SparePart.unit_cost).label("value"))
                .where(SparePart.is_active == True)
                .group_by(SparePart.category)
            )
            categories = [{"category": r[0] or "other", "count": r[1], "value": round(float(r[2] or 0), 2)}
                          for r in cat_result.all()]

            return {
                "most_used_parts": most_used_list,
                "least_used_parts": least_used[:10],
                "stock_aging": aging_list,
                "category_breakdown": categories,
            }
        except Exception as e:
            logger.warning(f"Error in inventory analytics: {e}")
            return {}

    # ==================== COST ANALYTICS ====================

    @staticmethod
    async def get_cost_analytics(db: AsyncSession, days: int = 365) -> Dict[str, Any]:
        try:
            since = datetime.utcnow() - timedelta(days=days)

            # Total costs breakdown
            total_labour = float((await db.execute(
                select(func.sum(WorkshopJob.labour_cost)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since)
                )
            )).scalar() or 0)

            total_parts = float((await db.execute(
                select(func.sum(WorkshopJob.parts_cost)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since)
                )
            )).scalar() or 0)

            total_misc = float((await db.execute(
                select(func.sum(WorkshopJob.misc_cost)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since)
                )
            )).scalar() or 0)

            total_maint = float((await db.execute(
                select(func.sum(MaintenanceLog.cost)).where(
                    and_(MaintenanceLog.service_date >= since, MaintenanceLog.cost > 0)
                )
            )).scalar() or 0)

            # Monthly cost trend
            monthly = await db.execute(
                select(func.strftime("%Y-%m", WorkshopJob.created_date).label("month"),
                       func.sum(WorkshopJob.labour_cost).label("labour"),
                       func.sum(WorkshopJob.parts_cost).label("parts"),
                       func.sum(WorkshopJob.misc_cost).label("misc"),
                       func.sum(WorkshopJob.total_cost).label("total"),
                       func.count().label("jobs"))
                .where(and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since))
                .group_by("month").order_by("month")
            )
            monthly_trend = []
            for row in monthly.all():
                monthly_trend.append({
                    "month": row[0], "labour": round(float(row[1] or 0), 2),
                    "parts": round(float(row[2] or 0), 2), "misc": round(float(row[3] or 0), 2),
                    "total": round(float(row[4] or 0), 2), "jobs": row[5],
                })

            # Vehicle-wise cost
            vehicle_cost = await db.execute(
                select(WorkshopJob.device_id, func.sum(WorkshopJob.total_cost).label("total"),
                       func.count().label("jobs"))
                .where(and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since))
                .group_by(WorkshopJob.device_id).order_by(desc("total")).limit(10)
            )
            vehicle_costs = []
            for row in vehicle_cost.all():
                dev = (await db.execute(select(Device).where(Device.id == row[0]))).scalar_one_or_none()
                vehicle_costs.append({
                    "device_id": row[0], "device_name": dev.name if dev else f"Vehicle {row[0]}",
                    "total_cost": round(float(row[1] or 0), 2), "jobs": row[2],
                })

            # Category-wise cost (by maintenance type)
            type_cost = await db.execute(
                select(MaintenanceType.name, func.sum(WorkshopJob.total_cost).label("total"), func.count().label("jobs"))
                .join(WorkshopJob, WorkshopJob.type_id == MaintenanceType.id, isouter=True)
                .where(and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since))
                .group_by(MaintenanceType.name).order_by(desc("total"))
            )
            category_costs = [{"category": r[0] or "Unknown", "total_cost": round(float(r[1] or 0), 2), "jobs": r[2]}
                              for r in type_cost.all()]

            return {
                "total_labour_cost": round(total_labour, 2),
                "total_parts_cost": round(total_parts, 2),
                "total_misc_cost": round(total_misc, 2),
                "total_maintenance_cost": round(total_maint, 2),
                "monthly_trend": monthly_trend,
                "vehicle_costs": vehicle_costs,
                "category_costs": category_costs,
                "days": days,
            }
        except Exception as e:
            logger.warning(f"Error in cost analytics: {e}")
            return {}

    # ==================== MONTHLY / YEARLY REPORTS ====================

    @staticmethod
    async def get_monthly_report(db: AsyncSession, year: int = None, month: int = None) -> Dict[str, Any]:
        try:
            now = datetime.utcnow()
            year = year or now.year
            month = month or now.month
            month_start = datetime(year, month, 1)
            month_end = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59)

            jobs_created = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(
                    and_(WorkshopJob.created_date >= month_start, WorkshopJob.created_date <= month_end)
                )
            )).scalar() or 0

            jobs_completed = (await db.execute(
                select(func.count()).select_from(WorkshopJob).where(
                    and_(WorkshopJob.status == "completed",
                         WorkshopJob.completed_date >= month_start, WorkshopJob.completed_date <= month_end)
                )
            )).scalar() or 0

            total_cost = float((await db.execute(
                select(func.sum(WorkshopJob.total_cost)).where(
                    and_(WorkshopJob.status == "completed",
                         WorkshopJob.completed_date >= month_start, WorkshopJob.completed_date <= month_end)
                )
            )).scalar() or 0)

            maint_logs = (await db.execute(
                select(func.count()).select_from(MaintenanceLog).where(
                    and_(MaintenanceLog.service_date >= month_start, MaintenanceLog.service_date <= month_end)
                )
            )).scalar() or 0

            maint_cost = float((await db.execute(
                select(func.sum(MaintenanceLog.cost)).where(
                    and_(MaintenanceLog.service_date >= month_start, MaintenanceLog.service_date <= month_end,
                         MaintenanceLog.cost > 0)
                )
            )).scalar() or 0)

            parts_issued = float((await db.execute(
                select(func.sum(func.abs(StockMovement.quantity))).where(
                    and_(StockMovement.movement_type == "stock_out",
                         StockMovement.created_at >= month_start, StockMovement.created_at <= month_end)
                )
            )).scalar() or 0)

            return {
                "year": year, "month": month,
                "month_name": calendar.month_name[month],
                "jobs_created": jobs_created, "jobs_completed": jobs_completed,
                "workshop_cost": round(total_cost, 2),
                "maintenance_services": maint_logs, "maintenance_cost": round(maint_cost, 2),
                "parts_consumed": round(parts_issued, 2),
                "total_cost": round(total_cost + maint_cost, 2),
            }
        except Exception as e:
            logger.warning(f"Error in monthly report: {e}")
            return {}

    @staticmethod
    async def get_yearly_report(db: AsyncSession, year: int = None) -> Dict[str, Any]:
        try:
            year = year or datetime.utcnow().year
            year_start = datetime(year, 1, 1)
            year_end = datetime(year, 12, 31, 23, 59, 59)

            monthly_data = []
            for m in range(1, 13):
                m_start = datetime(year, m, 1)
                m_end = datetime(year, m, calendar.monthrange(year, m)[1], 23, 59, 59)

                jobs = (await db.execute(
                    select(func.count()).select_from(WorkshopJob).where(
                        and_(WorkshopJob.created_date >= m_start, WorkshopJob.created_date <= m_end)
                    )
                )).scalar() or 0

                cost = float((await db.execute(
                    select(func.sum(WorkshopJob.total_cost)).where(
                        and_(WorkshopJob.status == "completed",
                             WorkshopJob.completed_date >= m_start, WorkshopJob.completed_date <= m_end)
                    )
                )).scalar() or 0)

                monthly_data.append({
                    "month": m, "month_name": calendar.month_name[m],
                    "jobs": jobs, "cost": round(cost, 2),
                })

            total_jobs = sum(d["jobs"] for d in monthly_data)
            total_cost = sum(d["cost"] for d in monthly_data)

            return {
                "year": year, "total_jobs": total_jobs, "total_cost": round(total_cost, 2),
                "monthly_data": monthly_data,
            }
        except Exception as e:
            logger.warning(f"Error in yearly report: {e}")
            return {}

    # ==================== VEHICLE DOWNTIME ====================

    @staticmethod
    async def get_vehicle_downtime(db: AsyncSession, days: int = 90) -> List[Dict[str, Any]]:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            jobs = await db.execute(
                select(WorkshopJob.device_id,
                       func.count().label("visit_count"),
                       func.sum(WorkshopJob.labour_hours).label("total_hours"),
                       func.sum(WorkshopJob.total_cost).label("total_cost"),
                       func.min(WorkshopJob.created_date).label("first_visit"),
                       func.max(WorkshopJob.completed_date).label("last_visit"))
                .where(and_(WorkshopJob.status == "completed", WorkshopJob.created_date >= since))
                .group_by(WorkshopJob.device_id)
                .order_by(desc("total_hours"))
            )
            results = []
            for row in jobs.all():
                dev = (await db.execute(select(Device).where(Device.id == row[0]))).scalar_one_or_none()
                results.append({
                    "device_id": row[0], "device_name": dev.name if dev else f"Vehicle {row[0]}",
                    "visit_count": row[1], "total_hours": round(float(row[2] or 0), 1),
                    "total_cost": round(float(row[3] or 0), 2),
                    "first_visit": row[4].isoformat() if row[4] else None,
                    "last_visit": row[5].isoformat() if row[5] else None,
                })
            return results
        except Exception as e:
            logger.warning(f"Error in vehicle downtime: {e}")
            return []

    # ==================== LOW STOCK REPORT ====================

    @staticmethod
    async def get_low_stock_report(db: AsyncSession) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(SparePart).where(
                    and_(SparePart.is_active == True, SparePart.current_quantity <= SparePart.minimum_stock)
                ).order_by(SparePart.current_quantity)
            )
            report = []
            for p in result.scalars().all():
                deficit = max(0, p.minimum_stock - p.current_quantity)
                report.append({
                    "part_id": p.id, "part_number": p.part_number, "name": p.name,
                    "category": p.category, "unit": p.unit,
                    "current_stock": p.current_quantity, "minimum_stock": p.minimum_stock,
                    "deficit": deficit, "reorder_cost": round(deficit * p.unit_cost, 2),
                    "supplier": p.supplier,
                    "status": "OUT_OF_STOCK" if p.current_quantity <= 0 else "LOW_STOCK",
                })
            return report
        except Exception as e:
            logger.warning(f"Error in low stock report: {e}")
            return []

    # ==================== PARTS USAGE BY JOB ====================

    @staticmethod
    async def get_parts_usage_by_job(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            result = await db.execute(
                select(StockMovement.reference_number, StockMovement.reference_id,
                       func.count().label("parts_count"),
                       func.sum(StockMovement.total_cost).label("total_cost"))
                .where(and_(StockMovement.reference_type == "workshop_job",
                            StockMovement.created_at >= since))
                .group_by(StockMovement.reference_number, StockMovement.reference_id)
                .order_by(desc("total_cost"))
            )
            usage = []
            for row in result.all():
                usage.append({
                    "job_id": row[1], "job_number": row[0],
                    "parts_count": row[2],
                    "total_parts_cost": round(float(row[3] or 0), 2),
                })
            return usage
        except Exception as e:
            logger.warning(f"Error in parts usage by job: {e}")
            return []

    # ==================== CHART DATA ====================

    @staticmethod
    async def get_maintenance_cost_trend(db: AsyncSession, months: int = 12) -> Dict[str, Any]:
        try:
            since = datetime.utcnow() - timedelta(days=months * 30)
            result = await db.execute(
                select(func.strftime("%Y-%m", MaintenanceLog.service_date).label("month"),
                       func.sum(MaintenanceLog.cost).label("cost"), func.count().label("count"))
                .where(and_(MaintenanceLog.service_date >= since, MaintenanceLog.cost > 0))
                .group_by("month").order_by("month")
            )
            labels, costs, counts = [], [], []
            for row in result.all():
                labels.append(row[0])
                costs.append(round(float(row[1] or 0), 2))
                counts.append(row[2])
            return {"labels": labels, "costs": costs, "counts": counts}
        except Exception as e:
            logger.warning(f"Error in cost trend: {e}")
            return {"labels": [], "costs": [], "counts": []}

    @staticmethod
    async def get_job_status_distribution(db: AsyncSession) -> Dict[str, Any]:
        try:
            result = await db.execute(
                select(WorkshopJob.status, func.count().label("cnt"))
                .group_by(WorkshopJob.status)
            )
            labels, values = [], []
            for row in result.all():
                labels.append(row[0].replace("_", " ").title())
                values.append(row[1])
            return {"labels": labels, "values": values}
        except Exception as e:
            logger.warning(f"Error in status distribution: {e}")
            return {"labels": [], "values": []}

    @staticmethod
    async def get_inventory_value_by_category(db: AsyncSession) -> Dict[str, Any]:
        try:
            result = await db.execute(
                select(SparePart.category, func.sum(SparePart.current_quantity * SparePart.unit_cost).label("value"))
                .where(SparePart.is_active == True)
                .group_by(SparePart.category)
            )
            labels, values = [], []
            for row in result.all():
                labels.append((row[0] or "Other").title())
                values.append(round(float(row[1] or 0), 2))
            return {"labels": labels, "values": values}
        except Exception as e:
            logger.warning(f"Error in inventory value by category: {e}")
            return {"labels": [], "values": []}


reports_service = ReportsService()
