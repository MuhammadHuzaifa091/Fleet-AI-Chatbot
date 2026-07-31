from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.traccar import (
    Device, MaintenanceType, MaintenanceRule, MaintenanceTemplate,
    VehicleMaintenancePlan, VehiclePlanRuleOverride, MaintenanceLog,
    Workshop, Technician, WorkshopJob, JobNote, WorkshopAttachment,
    RuleHistory, Position
)
from app.services.traccar_api_client import get_traccar_client
from app.services.maintenance_planner_service import MaintenancePlannerService
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta
import uuid


class WorkshopService:
    """Workshop Management service — Enterprise Job Lifecycle"""

    VALID_STATUSES = [
        "pending", "assigned", "vehicle_arrived", "inspection",
        "in_progress", "waiting_parts", "paused",
        "quality_check", "approved", "completed", "cancelled"
    ]
    VALID_PRIORITIES = ["low", "medium", "high", "critical"]

    VALID_TRANSITIONS = {
        "pending": ["assigned", "cancelled"],
        "assigned": ["vehicle_arrived", "cancelled"],
        "vehicle_arrived": ["inspection", "cancelled"],
        "inspection": ["in_progress", "cancelled"],
        "in_progress": ["waiting_parts", "paused", "quality_check", "cancelled"],
        "waiting_parts": ["in_progress", "cancelled"],
        "paused": ["in_progress", "cancelled"],
        "quality_check": ["in_progress", "approved", "cancelled"],
        "approved": ["completed", "cancelled"],
        "completed": [],
        "cancelled": [],
    }

    DEFAULT_CHECKLIST = [
        "Engine Oil Changed",
        "Oil Filter Installed",
        "Air Filter Checked",
        "Leak Inspection",
        "Road Test",
        "Cleaning",
        "Supervisor Approval",
    ]

    # ==================== JOB NUMBER GENERATION ====================

    @staticmethod
    def _generate_job_number() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d")
        short_id = uuid.uuid4().hex[:6].upper()
        return f"WJ-{ts}-{short_id}"

    # ==================== STATUS VALIDATION ====================

    @staticmethod
    def _validate_transition(current_status: str, new_status: str) -> bool:
        allowed = WorkshopService.VALID_TRANSITIONS.get(current_status, [])
        return new_status in allowed

    # ==================== WORKSHOP DASHBOARD ====================

    @staticmethod
    async def get_workshop_dashboard(db: AsyncSession) -> Dict[str, Any]:
        try:
            total_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob))).scalar() or 0
            active_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"])
            ))).scalar() or 0
            pending_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                WorkshopJob.status == "pending"
            ))).scalar() or 0
            completed_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                WorkshopJob.status == "completed"
            ))).scalar() or 0
            overdue_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                and_(WorkshopJob.status.in_(["pending", "assigned"]),
                     WorkshopJob.due_date < datetime.utcnow())
            ))).scalar() or 0
            cancelled_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                WorkshopJob.status == "cancelled"
            ))).scalar() or 0

            vehicles_in_workshop = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                WorkshopJob.status.in_(["vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"])
            ))).scalar() or 0

            avg_repair_hours = 0
            avg_result = await db.execute(
                select(func.avg(WorkshopJob.labour_hours)).where(
                    and_(WorkshopJob.status == "completed", WorkshopJob.labour_hours > 0)
                )
            )
            avg_val = avg_result.scalar()
            if avg_val:
                avg_repair_hours = round(float(avg_val), 1)

            status_counts = {}
            for s in WorkshopService.VALID_STATUSES:
                cnt = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                    WorkshopJob.status == s
                ))).scalar() or 0
                status_counts[s] = cnt

            total_techs = (await db.execute(select(func.count()).select_from(Technician).where(
                Technician.is_active == True
            ))).scalar() or 0
            available_techs = (await db.execute(select(func.count()).select_from(Technician).where(
                and_(Technician.is_active == True, Technician.status == "available")
            ))).scalar() or 0
            busy_techs = (await db.execute(select(func.count()).select_from(Technician).where(
                and_(Technician.is_active == True, Technician.status == "busy")
            ))).scalar() or 0

            total_cost_result = await db.execute(
                select(func.sum(WorkshopJob.total_cost)).where(WorkshopJob.status == "completed")
            )
            total_cost = total_cost_result.scalar() or 0

            return {
                "kpis": {
                    "total_jobs": total_jobs,
                    "active_jobs": active_jobs,
                    "pending_jobs": pending_jobs,
                    "completed_jobs": completed_jobs,
                    "overdue_jobs": overdue_jobs,
                    "cancelled_jobs": cancelled_jobs,
                    "vehicles_in_workshop": vehicles_in_workshop,
                    "avg_repair_hours": avg_repair_hours,
                    "total_technicians": total_techs,
                    "available_technicians": available_techs,
                    "busy_technicians": busy_techs,
                    "total_maintenance_cost": round(float(total_cost), 2),
                },
                "status_counts": status_counts,
            }
        except Exception as e:
            logger.warning(f"Error in workshop dashboard: {e}")
            return {"kpis": {}, "status_counts": {}}

    # ==================== WORKSHOP JOBS ====================

    @staticmethod
    async def get_jobs(db: AsyncSession, page: int = 1, page_size: int = 50,
                       search: str = None, status: str = None, priority: str = None,
                       technician_id: int = None, device_id: int = None) -> Dict[str, Any]:
        try:
            query = select(WorkshopJob)
            conditions = []
            if search:
                conditions.append(or_(
                    WorkshopJob.job_number.ilike(f"%{search}%"),
                    WorkshopJob.title.ilike(f"%{search}%")
                ))
            if status:
                conditions.append(WorkshopJob.status == status)
            if priority:
                conditions.append(WorkshopJob.priority == priority)
            if technician_id:
                conditions.append(WorkshopJob.technician_id == technician_id)
            if device_id:
                conditions.append(WorkshopJob.device_id == device_id)
            if conditions:
                query = query.where(and_(*conditions))

            total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
            query = query.order_by(desc(WorkshopJob.created_at)).limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            jobs = result.scalars().all()

            items = []
            for j in jobs:
                tech_name = None
                if j.technician_id:
                    tech_result = await db.execute(select(Technician).where(Technician.id == j.technician_id))
                    tech = tech_result.scalar_one_or_none()
                    tech_name = tech.name if tech else None

                device_name = None
                try:
                    dev_result = await db.execute(select(Device).where(Device.id == j.device_id))
                    dev = dev_result.scalar_one_or_none()
                    device_name = dev.name if dev else None
                except Exception:
                    pass
                if not device_name:
                    try:
                        tc = await get_traccar_client()
                        devices = await tc.get_devices()
                        for d in devices:
                            if d.get("id") == j.device_id:
                                device_name = d.get("name", f"Vehicle {j.device_id}")
                                break
                    except Exception:
                        device_name = f"Vehicle {j.device_id}"

                type_name = None
                if j.type_id:
                    t_result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == j.type_id))
                    t = t_result.scalar_one_or_none()
                    type_name = t.name if t else None

                template_name = None
                if j.template_id:
                    tmp_result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == j.template_id))
                    tmp = tmp_result.scalar_one_or_none()
                    template_name = tmp.name if tmp else None

                items.append({
                    "id": j.id, "job_number": j.job_number,
                    "device_id": j.device_id, "device_name": device_name,
                    "template_id": j.template_id, "template_name": template_name,
                    "type_id": j.type_id, "type_name": type_name,
                    "plan_id": j.plan_id,
                    "title": j.title, "description": j.description,
                    "priority": j.priority, "status": j.status,
                    "technician_id": j.technician_id, "technician_name": tech_name,
                    "workshop_id": j.workshop_id,
                    "current_odometer": j.current_odometer,
                    "due_reason": j.due_reason,
                    "created_date": j.created_date.isoformat() if j.created_date else None,
                    "started_date": j.started_date.isoformat() if j.started_date else None,
                    "completed_date": j.completed_date.isoformat() if j.completed_date else None,
                    "due_date": j.due_date.isoformat() if j.due_date else None,
                    "estimated_cost": j.estimated_cost,
                    "actual_cost": j.actual_cost,
                    "total_cost": j.total_cost,
                    "labour_hours": j.labour_hours,
                    "labour_cost": j.labour_cost,
                    "parts_cost": j.parts_cost,
                    "misc_cost": j.misc_cost,
                    "quality_check_passed": j.quality_check_passed,
                    "approved": j.approved,
                    "next_due_km": j.next_due_km,
                    "next_due_date": j.next_due_date.isoformat() if j.next_due_date else None,
                    "created_at": j.created_at.isoformat() if j.created_at else None,
                })

            return {
                "items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        except Exception as e:
            logger.warning(f"Error in get_jobs: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    # ==================== CREATE JOB ====================

    @staticmethod
    async def create_job(db: AsyncSession, data: Dict[str, Any], created_by: int = None) -> WorkshopJob:
        try:
            device_id = data.get("device_id")
            device_name = data.get("device_name", "")

            device = None
            try:
                dev_result = await db.execute(select(Device).where(Device.id == device_id))
                device = dev_result.scalar_one_or_none()
            except Exception:
                pass
            if not device:
                try:
                    tc = await get_traccar_client()
                    devices = await tc.get_devices()
                    for d in devices:
                        if d.get("id") == device_id:
                            device_name = device_name or d.get("name", f"Vehicle {device_id}")
                            break
                except Exception:
                    device_name = device_name or f"Vehicle {device_id}"

            current_km = 0
            try:
                tc = await get_traccar_client()
                positions = await tc.get_device_positions(device_id)
                if positions:
                    attrs = positions[0].get("attributes", {}) or {}
                    total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
                    current_km = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)
            except Exception:
                pass

            job = WorkshopJob(
                job_number=WorkshopService._generate_job_number(),
                device_id=device_id,
                template_id=data.get("template_id"),
                type_id=data.get("type_id"),
                plan_id=data.get("plan_id"),
                title=data.get("title", f"Maintenance - {device_name}"),
                description=data.get("description", ""),
                priority=data.get("priority", "medium"),
                status="pending",
                workshop_id=data.get("workshop_id"),
                current_odometer=current_km,
                due_reason=data.get("due_reason", ""),
                due_date=datetime.fromisoformat(data["due_date"]) if data.get("due_date") else None,
                estimated_cost=data.get("estimated_cost"),
                notes=data.get("notes", ""),
                created_by=created_by,
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)

            await WorkshopService._add_timeline_event(db, job.id, "job_created", "Job created", f"User {created_by}")

            return job
        except Exception as e:
            logger.warning(f"Error creating job: {e}")
            raise

    # ==================== GET JOB DETAIL ====================

    @staticmethod
    async def get_job_detail(db: AsyncSession, job_id: int) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            device_name = None
            try:
                dev_result = await db.execute(select(Device).where(Device.id == job.device_id))
                dev = dev_result.scalar_one_or_none()
                device_name = dev.name if dev else None
            except Exception:
                pass
            if not device_name:
                try:
                    tc = await get_traccar_client()
                    devices = await tc.get_devices()
                    for d in devices:
                        if d.get("id") == job.device_id:
                            device_name = d.get("name", f"Vehicle {job.device_id}")
                            break
                except Exception:
                    device_name = f"Vehicle {job.device_id}"

            type_name = None
            if job.type_id:
                t_result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == job.type_id))
                t = t_result.scalar_one_or_none()
                type_name = t.name if t else None

            template_name = None
            if job.template_id:
                tmp_result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == job.template_id))
                tmp = tmp_result.scalar_one_or_none()
                template_name = tmp.name if tmp else None

            tech_name = None
            if job.technician_id:
                tech_result = await db.execute(select(Technician).where(Technician.id == job.technician_id))
                tech = tech_result.scalar_one_or_none()
                tech_name = tech.name if tech else None

            history = []
            hist_result = await db.execute(
                select(MaintenanceLog).where(MaintenanceLog.device_id == job.device_id)
                .order_by(desc(MaintenanceLog.service_date)).limit(10)
            )
            for log in hist_result.scalars().all():
                history.append({
                    "id": log.id, "service_date": log.service_date.isoformat() if log.service_date else None,
                    "service_value": log.service_value, "service_type": log.service_type,
                    "technician": log.technician, "cost": log.cost, "notes": log.notes,
                })

            timeline = []
            tl_result = await db.execute(
                select(JobNote).where(JobNote.job_id == job.id).order_by(desc(JobNote.created_at))
            )
            for n in tl_result.scalars().all():
                timeline.append({
                    "id": n.id, "note_type": n.note_type, "content": n.content,
                    "author": n.author, "created_at": n.created_at.isoformat() if n.created_at else None,
                })

            attachments = []
            att_result = await db.execute(
                select(WorkshopAttachment).where(WorkshopAttachment.job_id == job.id).order_by(desc(WorkshopAttachment.created_at))
            )
            for a in att_result.scalars().all():
                attachments.append({
                    "id": a.id, "filename": a.filename, "original_name": a.original_name,
                    "file_type": a.file_type, "file_size": a.file_size,
                    "uploaded_by": a.uploaded_by,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                })

            return {
                "id": job.id, "job_number": job.job_number,
                "device_id": job.device_id, "device_name": device_name,
                "template_id": job.template_id, "template_name": template_name,
                "type_id": job.type_id, "type_name": type_name,
                "plan_id": job.plan_id,
                "title": job.title, "description": job.description,
                "priority": job.priority, "status": job.status,
                "technician_id": job.technician_id, "technician_name": tech_name,
                "workshop_id": job.workshop_id,
                "current_odometer": job.current_odometer,
                "due_reason": job.due_reason,
                "created_date": job.created_date.isoformat() if job.created_date else None,
                "started_date": job.started_date.isoformat() if job.started_date else None,
                "completed_date": job.completed_date.isoformat() if job.completed_date else None,
                "due_date": job.due_date.isoformat() if job.due_date else None,
                "vehicle_arrived_date": job.vehicle_arrived_date.isoformat() if job.vehicle_arrived_date else None,
                "inspection_date": job.inspection_date.isoformat() if job.inspection_date else None,
                "paused_date": job.paused_date.isoformat() if job.paused_date else None,
                "resumed_date": job.resumed_date.isoformat() if job.resumed_date else None,
                "estimated_cost": job.estimated_cost,
                "actual_cost": job.actual_cost,
                "total_cost": job.total_cost,
                "labour_hours": job.labour_hours,
                "labour_cost": job.labour_cost,
                "parts_cost": job.parts_cost,
                "misc_cost": job.misc_cost,
                "parts_used": job.parts_used or [],
                "notes": job.notes, "internal_notes": job.internal_notes,
                "quality_check_passed": job.quality_check_passed,
                "quality_check_notes": job.quality_check_notes,
                "quality_checked_by": job.quality_checked_by,
                "quality_check_date": job.quality_check_date.isoformat() if job.quality_check_date else None,
                "quality_checklist": job.quality_checklist or [],
                "approved": job.approved,
                "approved_by": job.approved_by,
                "approved_date": job.approved_date.isoformat() if job.approved_date else None,
                "maintenance_log_id": job.maintenance_log_id,
                "next_due_km": job.next_due_km,
                "next_due_date": job.next_due_date.isoformat() if job.next_due_date else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "maintenance_history": history,
                "timeline": timeline,
                "attachments": attachments,
                "valid_transitions": WorkshopService.VALID_TRANSITIONS.get(job.status, []),
            }
        except Exception as e:
            logger.warning(f"Error in get_job_detail: {e}")
            return None

    # ==================== UPDATE JOB ====================

    @staticmethod
    async def update_job(db: AsyncSession, job_id: int, data: Dict[str, Any], updated_by: int = None) -> Optional[WorkshopJob]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            old_status = job.status
            new_status = data.get("status", old_status)

            if new_status != old_status:
                if not WorkshopService._validate_transition(old_status, new_status):
                    raise ValueError(f"Invalid transition: {old_status} -> {new_status}")

            now = datetime.utcnow()

            if new_status == "vehicle_arrived" and old_status != "vehicle_arrived":
                job.vehicle_arrived_date = now
                await WorkshopService._add_timeline_event(db, job.id, "vehicle_arrived", "Vehicle arrived at workshop", f"User {updated_by}")

            if new_status == "inspection" and old_status != "inspection":
                job.inspection_date = now
                await WorkshopService._add_timeline_event(db, job.id, "inspection_started", "Inspection started", f"User {updated_by}")

            if new_status == "in_progress" and not job.started_date:
                job.started_date = now
                await WorkshopService._add_timeline_event(db, job.id, "maintenance_started", "Maintenance started", f"User {updated_by}")

            if new_status == "paused":
                job.paused_date = now
                await WorkshopService._add_timeline_event(db, job.id, "paused", "Job paused", f"User {updated_by}")

            if new_status == "in_progress" and old_status == "paused":
                job.resumed_date = now
                await WorkshopService._add_timeline_event(db, job.id, "resumed", "Job resumed", f"User {updated_by}")

            if new_status == "quality_check":
                await WorkshopService._add_timeline_event(db, job.id, "quality_check", "Quality check initiated", f"User {updated_by}")

            if new_status == "approved":
                job.approved = True
                job.approved_by = data.get("approved_by", f"User {updated_by}")
                job.approved_date = now
                await WorkshopService._add_timeline_event(db, job.id, "approved", f"Job approved by {job.approved_by}", job.approved_by)

            job.status = new_status
            if "technician_id" in data:
                old_tech = job.technician_id
                job.technician_id = data["technician_id"]
                if data["technician_id"] and data["technician_id"] != old_tech:
                    tech_result = await db.execute(select(Technician).where(Technician.id == data["technician_id"]))
                    tech = tech_result.scalar_one_or_none()
                    if tech:
                        await WorkshopService._add_timeline_event(db, job.id, "assigned", f"Assigned to {tech.name}", f"User {updated_by}")
                        active_count = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                            and_(WorkshopJob.technician_id == tech.id,
                                 WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"]))
                        ))).scalar() or 0
                        max_wl = tech.max_workload or 3
                        if active_count >= max_wl:
                            raise ValueError(f"Technician {tech.name} is at max workload ({active_count}/{max_wl})")
                        tech.status = "busy"

            if "priority" in data:
                job.priority = data["priority"]
            if "notes" in data:
                job.notes = data["notes"]
            if "internal_notes" in data:
                job.internal_notes = data["internal_notes"]
            if "estimated_cost" in data:
                job.estimated_cost = data["estimated_cost"]
            if "due_date" in data:
                job.due_date = datetime.fromisoformat(data["due_date"]) if data["due_date"] else None

            if "labour_hours" in data:
                job.labour_hours = data["labour_hours"]
            if "labour_cost" in data:
                job.labour_cost = data["labour_cost"]
            if "parts_cost" in data:
                job.parts_cost = data["parts_cost"]
            if "misc_cost" in data:
                job.misc_cost = data["misc_cost"]
            if "parts_used" in data:
                job.parts_used = data["parts_used"]

            job.total_cost = (job.labour_cost or 0) + (job.parts_cost or 0) + (job.misc_cost or 0)
            job.actual_cost = job.total_cost

            job.updated_at = now
            await db.commit()
            await db.refresh(job)

            return job
        except Exception as e:
            logger.warning(f"Error updating job: {e}")
            raise

    # ==================== STATUS TRANSITION ====================

    @staticmethod
    async def transition_status(db: AsyncSession, job_id: int, new_status: str, data: Dict[str, Any] = None, changed_by: int = None) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            if not WorkshopService._validate_transition(job.status, new_status):
                raise ValueError(f"Invalid transition: {job.status} -> {new_status}")

            update_data = {"status": new_status}
            if data:
                update_data.update(data)

            job = await WorkshopService.update_job(db, job_id, update_data, changed_by)
            if not job:
                return None

            return {
                "id": job.id, "job_number": job.job_number,
                "status": job.status, "message": f"Status changed to {new_status}"
            }
        except Exception as e:
            logger.warning(f"Error transitioning status: {e}")
            raise

    # ==================== QUALITY CHECK ====================

    @staticmethod
    async def quality_check(db: AsyncSession, job_id: int, data: Dict[str, Any], checked_by: int = None) -> Optional[WorkshopJob]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            checklist = data.get("checklist", [])
            if not checklist:
                checklist = [{"item": item, "passed": False, "remarks": ""} for item in WorkshopService.DEFAULT_CHECKLIST]

            all_passed = all(c.get("passed", False) for c in checklist)

            job.quality_check_passed = all_passed
            job.quality_check_notes = data.get("notes", "")
            job.quality_checked_by = data.get("checked_by_name", f"User {checked_by}")
            job.quality_check_date = datetime.utcnow()
            job.quality_checklist = checklist

            if all_passed:
                job.status = "quality_check"
            else:
                job.status = "in_progress"

            await WorkshopService._add_timeline_event(
                db, job.id, "quality_check",
                f"Quality check {'PASSED' if all_passed else 'FAILED'}: {job.quality_check_notes}",
                job.quality_checked_by
            )

            job.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(job)
            return job
        except Exception as e:
            logger.warning(f"Error in quality check: {e}")
            raise

    # ==================== APPROVE JOB ====================

    @staticmethod
    async def approve_job(db: AsyncSession, job_id: int, data: Dict[str, Any], approved_by: int = None) -> Optional[WorkshopJob]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            if job.status != "quality_check":
                raise ValueError("Job must be in quality_check status to approve")
            if not job.quality_check_passed:
                raise ValueError("Quality check must pass before approval")

            job.approved = True
            job.approved_by = data.get("approved_by", f"User {approved_by}")
            job.approved_date = datetime.utcnow()
            job.status = "approved"

            await WorkshopService._add_timeline_event(
                db, job.id, "approved",
                f"Job approved by {job.approved_by}",
                job.approved_by
            )

            job.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(job)
            return job
        except Exception as e:
            logger.warning(f"Error approving job: {e}")
            raise

    # ==================== COMPLETE JOB ====================

    @staticmethod
    async def complete_job(db: AsyncSession, job_id: int, data: Dict[str, Any], completed_by: int = None) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None

            if job.status not in ["approved", "quality_check"]:
                if not job.approved and job.quality_check_passed:
                    pass
                else:
                    raise ValueError("Job must be approved before completion")

            job.status = "completed"
            job.completed_date = datetime.utcnow()
            job.labour_hours = data.get("labour_hours", 0)
            job.labour_cost = data.get("labour_cost", 0)
            job.parts_cost = data.get("parts_cost", 0)
            job.misc_cost = data.get("misc_cost", 0)
            job.total_cost = (job.labour_cost or 0) + (job.parts_cost or 0) + (job.misc_cost or 0)
            job.actual_cost = data.get("actual_cost") or job.total_cost
            job.parts_used = data.get("parts_used", [])
            if data.get("notes"):
                job.notes = data["notes"]

            await WorkshopService._add_timeline_event(
                db, job.id, "completed",
                f"Job completed. Total cost: {job.total_cost}, Hours: {job.labour_hours}",
                f"User {completed_by}"
            )

            tc = await get_traccar_client()
            positions = await tc.get_device_positions(job.device_id)
            current_km = 0
            if positions:
                attrs = positions[0].get("attributes", {}) or {}
                total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
                current_km = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)

            log_id = None
            try:
                schedule_result = await db.execute(
                    select(MaintenanceLog).where(MaintenanceLog.device_id == job.device_id)
                    .order_by(desc(MaintenanceLog.id)).limit(1)
                )
                last_log = schedule_result.scalar_one_or_none()
                schedule_id = last_log.schedule_id if last_log else 1

                tech_name = None
                if job.technician_id:
                    tech_result = await db.execute(select(Technician).where(Technician.id == job.technician_id))
                    tech = tech_result.scalar_one_or_none()
                    tech_name = tech.name if tech else None

                log = MaintenanceLog(
                    device_id=job.device_id,
                    schedule_id=schedule_id,
                    service_date=datetime.utcnow(),
                    service_value=current_km,
                    service_type="scheduled",
                    workshop_id=job.workshop_id,
                    technician=tech_name,
                    cost=job.total_cost,
                    notes=job.notes or f"Completed via workshop job {job.job_number}",
                    parts_replaced=job.parts_used,
                    previous_odometer=job.current_odometer,
                    odometer_difference=round(current_km - (job.current_odometer or 0), 2) if job.current_odometer else None,
                    created_by=completed_by,
                )
                db.add(log)
                await db.commit()
                await db.refresh(log)
                log_id = log.id
                job.maintenance_log_id = log.id
            except Exception as log_err:
                logger.warning(f"Error creating maintenance log: {log_err}")

            next_due_km = None
            next_due_date = None
            if job.type_id:
                try:
                    type_result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == job.type_id))
                    mtype = type_result.scalar_one_or_none()
                    if mtype:
                        if mtype.default_interval_km:
                            next_due_km = round(current_km + mtype.default_interval_km, 2)
                        if mtype.default_interval_days:
                            next_due_date = datetime.utcnow() + timedelta(days=mtype.default_interval_days)
                except Exception:
                    pass

            job.next_due_km = next_due_km
            job.next_due_date = next_due_date

            if job.technician_id:
                try:
                    tech_result = await db.execute(select(Technician).where(Technician.id == job.technician_id))
                    tech = tech_result.scalar_one_or_none()
                    if tech:
                        active_count = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                            and_(WorkshopJob.technician_id == tech.id,
                                 WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"]),
                                 WorkshopJob.id != job.id)
                        ))).scalar() or 0
                        tech.status = "available" if active_count == 0 else "busy"
                except Exception:
                    pass

            try:
                await MaintenancePlannerService.log_activity_event(
                    db, "workshop_job_completed",
                    f"Workshop job {job.job_number} completed for device {job.device_id}",
                    template_id=job.template_id, plan_id=job.plan_id, changed_by=completed_by
                )
            except Exception:
                pass

            await db.commit()
            await db.refresh(job)

            return {
                "job_id": job.id, "job_number": job.job_number,
                "status": job.status, "maintenance_log_id": log_id,
                "next_due_km": next_due_km,
                "next_due_date": next_due_date.isoformat() if next_due_date else None,
                "total_cost": job.total_cost,
            }
        except Exception as e:
            logger.warning(f"Error completing job: {e}")
            raise

    # ==================== CANCEL JOB ====================

    @staticmethod
    async def cancel_job(db: AsyncSession, job_id: int, reason: str = "", cancelled_by: int = None) -> Optional[WorkshopJob]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                return None
            if job.status in ["completed", "cancelled"]:
                raise ValueError(f"Cannot cancel job in {job.status} status")

            job.status = "cancelled"
            job.updated_at = datetime.utcnow()
            await WorkshopService._add_timeline_event(
                db, job.id, "cancelled", f"Job cancelled: {reason}", f"User {cancelled_by}"
            )

            if job.technician_id:
                try:
                    tech_result = await db.execute(select(Technician).where(Technician.id == job.technician_id))
                    tech = tech_result.scalar_one_or_none()
                    if tech:
                        active_count = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                            and_(WorkshopJob.technician_id == tech.id,
                                 WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"]),
                                 WorkshopJob.id != job.id)
                        ))).scalar() or 0
                        tech.status = "available" if active_count == 0 else "busy"
                except Exception:
                    pass

            await db.commit()
            await db.refresh(job)
            return job
        except Exception as e:
            logger.warning(f"Error cancelling job: {e}")
            raise

    # ==================== TIMELINE ====================

    @staticmethod
    async def get_timeline(db: AsyncSession, job_id: int) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(JobNote).where(JobNote.job_id == job_id).order_by(desc(JobNote.created_at))
            )
            timeline = []
            for n in result.scalars().all():
                timeline.append({
                    "id": n.id, "note_type": n.note_type, "content": n.content,
                    "author": n.author, "created_at": n.created_at.isoformat() if n.created_at else None,
                })
            return timeline
        except Exception as e:
            logger.warning(f"Error getting timeline: {e}")
            return []

    # ==================== ATTACHMENTS ====================

    @staticmethod
    async def add_attachment(db: AsyncSession, job_id: int, data: Dict[str, Any], uploaded_by: str = None) -> Optional[WorkshopAttachment]:
        try:
            result = await db.execute(select(WorkshopJob).where(WorkshopJob.id == job_id))
            if not result.scalar_one_or_none():
                return None

            att = WorkshopAttachment(
                job_id=job_id,
                filename=data.get("filename", ""),
                original_name=data.get("original_name", ""),
                file_type=data.get("file_type", "document"),
                file_size=data.get("file_size"),
                mime_type=data.get("mime_type"),
                uploaded_by=uploaded_by,
            )
            db.add(att)
            await db.commit()
            await db.refresh(att)

            await WorkshopService._add_timeline_event(
                db, job_id, "attachment_added",
                f"Attachment added: {att.original_name} ({att.file_type})",
                uploaded_by
            )

            return att
        except Exception as e:
            logger.warning(f"Error adding attachment: {e}")
            raise

    @staticmethod
    async def get_attachments(db: AsyncSession, job_id: int) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(WorkshopAttachment).where(WorkshopAttachment.job_id == job_id).order_by(desc(WorkshopAttachment.created_at))
            )
            attachments = []
            for a in result.scalars().all():
                attachments.append({
                    "id": a.id, "filename": a.filename, "original_name": a.original_name,
                    "file_type": a.file_type, "file_size": a.file_size,
                    "uploaded_by": a.uploaded_by,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                })
            return attachments
        except Exception as e:
            logger.warning(f"Error getting attachments: {e}")
            return []

    @staticmethod
    async def delete_attachment(db: AsyncSession, attachment_id: int) -> bool:
        try:
            result = await db.execute(select(WorkshopAttachment).where(WorkshopAttachment.id == attachment_id))
            att = result.scalar_one_or_none()
            if not att:
                return False
            await db.delete(att)
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"Error deleting attachment: {e}")
            return False

    # ==================== TECHNICIANS ====================

    @staticmethod
    async def get_technicians(db: AsyncSession, page: int = 1, page_size: int = 50,
                              search: str = None, status: str = None) -> Dict[str, Any]:
        try:
            query = select(Technician).where(Technician.is_active == True)
            conditions = []
            if search:
                conditions.append(or_(
                    Technician.name.ilike(f"%{search}%"),
                    Technician.employee_id.ilike(f"%{search}%")
                ))
            if status:
                conditions.append(Technician.status == status)
            if conditions:
                query = query.where(and_(*conditions))

            total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
            query = query.order_by(Technician.name).limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            techs = result.scalars().all()

            items = []
            for t in techs:
                active_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                    and_(WorkshopJob.technician_id == t.id,
                         WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"]))
                ))).scalar() or 0
                today_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                    and_(WorkshopJob.technician_id == t.id,
                         WorkshopJob.status.in_(["assigned", "vehicle_arrived", "inspection", "in_progress", "waiting_parts", "paused", "quality_check"]),
                         func.date(WorkshopJob.created_date) == datetime.utcnow().date())
                ))).scalar() or 0
                completed_jobs = (await db.execute(select(func.count()).select_from(WorkshopJob).where(
                    and_(WorkshopJob.technician_id == t.id, WorkshopJob.status == "completed")
                ))).scalar() or 0

                workshop_name = None
                if t.workshop_id:
                    ws_result = await db.execute(select(Workshop).where(Workshop.id == t.workshop_id))
                    ws = ws_result.scalar_one_or_none()
                    workshop_name = ws.name if ws else None

                max_wl = t.max_workload or 3
                workload_pct = round((active_jobs / max_wl) * 100) if max_wl > 0 else 0

                items.append({
                    "id": t.id, "name": t.name, "employee_id": t.employee_id,
                    "phone": t.phone, "email": t.email, "skills": t.skills or [],
                    "status": t.status, "workshop_id": t.workshop_id,
                    "workshop_name": workshop_name,
                    "max_workload": max_wl,
                    "active_jobs": active_jobs, "today_jobs": today_jobs,
                    "completed_jobs": completed_jobs,
                    "workload_percent": workload_pct,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                })

            return {
                "items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            }
        except Exception as e:
            logger.warning(f"Error in get_technicians: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    @staticmethod
    async def create_technician(db: AsyncSession, data: Dict[str, Any], created_by: int = None) -> Technician:
        try:
            existing = await db.execute(select(Technician).where(Technician.employee_id == data.get("employee_id")))
            if existing.scalar_one_or_none():
                raise ValueError(f"Employee ID {data.get('employee_id')} already exists")
            tech = Technician(
                name=data["name"], employee_id=data["employee_id"],
                phone=data.get("phone"), email=data.get("email"),
                skills=data.get("skills", []), status=data.get("status", "available"),
                max_workload=data.get("max_workload", 3),
                workshop_id=data.get("workshop_id"),
            )
            db.add(tech)
            await db.commit()
            await db.refresh(tech)
            return tech
        except Exception as e:
            logger.warning(f"Error creating technician: {e}")
            raise

    @staticmethod
    async def update_technician(db: AsyncSession, tech_id: int, data: Dict[str, Any]) -> Optional[Technician]:
        try:
            result = await db.execute(select(Technician).where(Technician.id == tech_id))
            tech = result.scalar_one_or_none()
            if not tech:
                return None
            for field in ["name", "phone", "email", "skills", "status", "workshop_id", "max_workload"]:
                if field in data:
                    setattr(tech, field, data[field])
            tech.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(tech)
            return tech
        except Exception as e:
            logger.warning(f"Error updating technician: {e}")
            raise

    @staticmethod
    async def delete_technician(db: AsyncSession, tech_id: int) -> bool:
        try:
            result = await db.execute(select(Technician).where(Technician.id == tech_id))
            tech = result.scalar_one_or_none()
            if not tech:
                return False
            tech.is_active = False
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"Error deleting technician: {e}")
            raise

    # ==================== CREATE FROM DUE/OVERDUE ====================

    @staticmethod
    async def create_job_from_due(db: AsyncSession, device_id: int, due_data: Dict[str, Any], created_by: int = None) -> Optional[WorkshopJob]:
        try:
            device_name = due_data.get("device_name", "")
            try:
                dev_result = await db.execute(select(Device).where(Device.id == device_id))
                device = dev_result.scalar_one_or_none()
                if device:
                    device_name = device.name
            except Exception:
                pass
            if not device_name:
                try:
                    tc = await get_traccar_client()
                    devices = await tc.get_devices()
                    for d in devices:
                        if d.get("id") == device_id:
                            device_name = d.get("name", f"Vehicle {device_id}")
                            break
                except Exception:
                    device_name = f"Vehicle {device_id}"

            type_name = due_data.get("type_name", "Maintenance")
            priority = due_data.get("priority", "medium")
            if priority == "critical":
                priority = "high"

            job_data = {
                "device_id": device_id,
                "type_id": due_data.get("type_id"),
                "template_id": due_data.get("template_id"),
                "plan_id": due_data.get("plan_id"),
                "title": f"{type_name} - {device_name}",
                "description": due_data.get("due_reason", f"{type_name} is due for {device_name}"),
                "priority": priority,
                "due_reason": due_data.get("due_reason", ""),
                "estimated_cost": due_data.get("estimated_cost"),
            }
            return await WorkshopService.create_job(db, job_data, created_by)
        except Exception as e:
            logger.warning(f"Error creating job from due: {e}")
            return None

    # ==================== HELPERS ====================

    @staticmethod
    async def _add_timeline_event(db: AsyncSession, job_id: int, action: str, content: str, author: str = None):
        try:
            note = JobNote(job_id=job_id, note_type=action, content=content, author=author)
            db.add(note)
            await db.commit()
        except Exception as e:
            logger.warning(f"Error adding timeline event: {e}")


workshop_service = WorkshopService()
