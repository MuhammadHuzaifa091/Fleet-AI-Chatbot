from sqlalchemy import select, func, and_, or_, desc, asc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.traccar import (
    Device, MaintenanceType, MaintenanceRule, MaintenanceTemplate,
    TemplateRuleLink, VehicleMaintenancePlan, VehiclePlanRuleOverride,
    RuleHistory, MaintenanceSchedule, VehicleMaintenance, Position, MaintenanceLog
)
from app.services.traccar_api_client import get_traccar_client
from typing import List, Dict, Any, Optional
from loguru import logger
from datetime import datetime, timedelta


class MaintenancePlannerService:
    """Maintenance Planner & Rule Engine service"""

    # Validation constraints
    VALIDATION = {
        "oil_change": {"min_km": 1000, "max_km": 100000, "min_days": 30, "max_days": 730},
        "filter_change": {"min_km": 500, "max_km": 50000, "min_days": 15, "max_days": 365},
        "brake_service": {"min_km": 1000, "max_km": 80000, "min_days": 30, "max_days": 1095},
        "tire_rotation": {"min_km": 5000, "max_km": 20000, "min_days": 30, "max_days": 365},
        "transmission": {"min_km": 5000, "max_km": 100000, "min_days": 90, "max_days": 2190},
        "coolant": {"min_km": 10000, "max_km": 100000, "min_days": 90, "max_days": 2190},
        "spark_plugs": {"min_km": 10000, "max_km": 60000, "min_days": 90, "max_days": 1095},
        "inspection": {"min_km": 1000, "max_km": 10000, "min_days": 7, "max_days": 365},
        "battery": {"min_km": 10000, "max_km": 100000, "min_days": 30, "max_days": 1460},
        "tyre_rotation": {"min_km": 5000, "max_km": 20000, "min_days": 30, "max_days": 365},
        "wheel_alignment": {"min_km": 10000, "max_km": 50000, "min_days": 30, "max_days": 730},
        "gear_oil": {"min_km": 10000, "max_km": 80000, "min_days": 90, "max_days": 2190},
        "transmission_oil": {"min_km": 10000, "max_km": 80000, "min_days": 90, "max_days": 2190},
        "timing_belt": {"min_km": 30000, "max_km": 120000, "min_days": 180, "max_days": 2190},
        "ac_service": {"min_km": 10000, "max_km": 50000, "min_days": 90, "max_days": 730},
        "general_inspection": {"min_km": 500, "max_km": 10000, "min_days": 7, "max_days": 365},
    }

    # ==================== MAINTENANCE TYPES ====================

    @staticmethod
    async def get_maintenance_types(db: AsyncSession, page: int = 1, page_size: int = 50,
                                     search: str = None, active_only: bool = None,
                                     deleted_only: bool = None, category: str = None,
                                     sort_by: str = "name", sort_order: str = "asc") -> Dict[str, Any]:
        try:
            query = select(MaintenanceType)
            conditions = []
            if search:
                conditions.append(
                    or_(MaintenanceType.name.ilike(f"%{search}%"),
                        MaintenanceType.slug.ilike(f"%{search}%"),
                        MaintenanceType.category.ilike(f"%{search}%"))
                )
            if active_only is True:
                conditions.append(MaintenanceType.is_active == True)
                conditions.append(MaintenanceType.is_deleted == False)
            elif active_only is False:
                conditions.append(MaintenanceType.is_active == False)
                conditions.append(MaintenanceType.is_deleted == False)
            if deleted_only is True:
                conditions.append(MaintenanceType.is_deleted == True)
            elif deleted_only is None and active_only is None:
                conditions.append(MaintenanceType.is_deleted == False)
            if category:
                conditions.append(MaintenanceType.category == category)

            if conditions:
                query = query.where(and_(*conditions))

            total_result = await db.execute(select(func.count()).select_from(MaintenanceType).where(and_(*conditions) if conditions else True))
            total = total_result.scalar() or 0

            if sort_by == "name":
                query = query.order_by(asc(MaintenanceType.name) if sort_order == "asc" else desc(MaintenanceType.name))
            elif sort_by == "category":
                query = query.order_by(asc(MaintenanceType.category) if sort_order == "asc" else desc(MaintenanceType.category))
            elif sort_by == "priority":
                query = query.order_by(asc(MaintenanceType.priority) if sort_order == "asc" else desc(MaintenanceType.priority))
            elif sort_by == "updated_at":
                query = query.order_by(asc(MaintenanceType.updated_at) if sort_order == "asc" else desc(MaintenanceType.updated_at))
            elif sort_by == "default_interval_km":
                query = query.order_by(asc(MaintenanceType.default_interval_km) if sort_order == "asc" else desc(MaintenanceType.default_interval_km))
            elif sort_by == "default_interval_days":
                query = query.order_by(asc(MaintenanceType.default_interval_days) if sort_order == "asc" else desc(MaintenanceType.default_interval_days))
            else:
                query = query.order_by(asc(MaintenanceType.name) if sort_order == "asc" else desc(MaintenanceType.name))

            query = query.limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            types = result.scalars().all()

            return {
                "items": [mt.to_dict() for mt in types],
                "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        except Exception as e:
            logger.warning(f"DB error in get_maintenance_types: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    @staticmethod
    async def create_maintenance_type(db: AsyncSession, data: Dict[str, Any], created_by: int = None) -> MaintenanceType:
        try:
            existing = await db.execute(select(MaintenanceType).where(
                MaintenanceType.name == data.get("name")
            ))
            if existing.scalar_one_or_none():
                raise ValueError(f"Maintenance type with name '{data.get('name')}' already exists")
            slug = data.get("slug") or data["name"].lower().replace(" ", "_")
            existing_slug = await db.execute(select(MaintenanceType).where(MaintenanceType.slug == slug))
            if existing_slug.scalar_one_or_none():
                raise ValueError(f"Maintenance type with slug '{slug}' already exists")
            mt = MaintenanceType(
                name=data["name"], slug=slug,
                description=data.get("description"), icon=data.get("icon"), color=data.get("color", "#3b82f6"),
                category=data.get("category"),
                default_interval_km=data.get("default_interval_km", 5000),
                default_interval_days=data.get("default_interval_days", 180),
                default_interval_hours=data.get("default_interval_hours"),
                default_engine_hours=data.get("default_engine_hours"),
                priority=data.get("priority", "medium"),
                is_active=data.get("is_active", True),
                is_system=data.get("is_system", False),
                created_by=created_by
            )
            db.add(mt)
            await db.commit()
            await db.refresh(mt)
            return mt
        except Exception as e:
            logger.warning(f"DB error in create_maintenance_type: {e}")
            raise

    @staticmethod
    async def update_maintenance_type(db: AsyncSession, type_id: int, data: Dict[str, Any], updated_by: int = None) -> Optional[MaintenanceType]:
        try:
            result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == type_id))
            mt = result.scalar_one_or_none()
            if not mt or mt.is_system:
                return None
            updatable = ["name", "slug", "description", "icon", "color", "category",
                         "default_interval_km", "default_interval_days", "default_interval_hours",
                         "default_engine_hours", "priority", "is_active"]
            for field in updatable:
                if field in data:
                    setattr(mt, field, data[field])
            mt.updated_by = updated_by
            mt.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(mt)
            return mt
        except Exception as e:
            logger.warning(f"DB error in update_maintenance_type: {e}")
            raise

    @staticmethod
    async def delete_maintenance_type(db: AsyncSession, type_id: int, deleted_by: int = None) -> bool:
        try:
            result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == type_id))
            mt = result.scalar_one_or_none()
            if not mt or mt.is_system:
                return False
            mt.is_deleted = True
            mt.is_active = False
            mt.updated_by = deleted_by
            mt.updated_at = datetime.utcnow()
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in delete_maintenance_type: {e}")
            raise

    @staticmethod
    async def restore_maintenance_type(db: AsyncSession, type_id: int, restored_by: int = None) -> Optional[MaintenanceType]:
        try:
            result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == type_id))
            mt = result.scalar_one_or_none()
            if not mt:
                return None
            mt.is_deleted = False
            mt.is_active = True
            mt.updated_by = restored_by
            mt.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(mt)
            return mt
        except Exception as e:
            logger.warning(f"DB error in restore_maintenance_type: {e}")
            raise

    @staticmethod
    async def get_maintenance_types_summary(db: AsyncSession) -> Dict[str, Any]:
        try:
            total = (await db.execute(select(func.count()).select_from(MaintenanceType))).scalar() or 0
            active = (await db.execute(select(func.count()).select_from(MaintenanceType).where(
                and_(MaintenanceType.is_active == True, MaintenanceType.is_deleted == False)))).scalar() or 0
            inactive = (await db.execute(select(func.count()).select_from(MaintenanceType).where(
                and_(MaintenanceType.is_active == False, MaintenanceType.is_deleted == False)))).scalar() or 0
            deleted = (await db.execute(select(func.count()).select_from(MaintenanceType).where(
                MaintenanceType.is_deleted == True))).scalar() or 0
            system = (await db.execute(select(func.count()).select_from(MaintenanceType).where(
                MaintenanceType.is_system == True))).scalar() or 0
            return {"total": total, "active": active, "inactive": inactive, "deleted": deleted, "system": system}
        except Exception as e:
            logger.warning(f"DB error in get_maintenance_types_summary: {e}")
            return {"total": 0, "active": 0, "inactive": 0, "deleted": 0, "system": 0}

    @staticmethod
    async def get_maintenance_categories(db: AsyncSession) -> List[str]:
        try:
            result = await db.execute(select(MaintenanceType.category).where(
                and_(MaintenanceType.category != None, MaintenanceType.category != "")
            ).distinct().order_by(MaintenanceType.category))
            return [row[0] for row in result.all()]
        except Exception as e:
            logger.warning(f"DB error in get_maintenance_categories: {e}")
            return []

    @staticmethod
    async def get_maintenance_type_by_id(db: AsyncSession, type_id: int) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == type_id))
            mt = result.scalar_one_or_none()
            return mt.to_dict() if mt else None
        except Exception as e:
            logger.warning(f"DB error in get_maintenance_type_by_id: {e}")
            return None

    @staticmethod
    async def seed_default_types(db: AsyncSession, created_by: int = None) -> int:
        try:
            existing_count = await db.execute(select(func.count()).select_from(MaintenanceType))
            if existing_count.scalar() > 0:
                return 0
            defaults = [
                {"name": "Engine Oil", "slug": "engine_oil", "category": "engine", "default_interval_km": 5000, "default_interval_days": 180, "priority": "critical", "is_system": True},
                {"name": "Oil Filter", "slug": "oil_filter", "category": "engine", "default_interval_km": 5000, "default_interval_days": 180, "priority": "high", "is_system": True},
                {"name": "Air Filter", "slug": "air_filter", "category": "engine", "default_interval_km": 10000, "default_interval_days": 365, "priority": "high"},
                {"name": "Fuel Filter", "slug": "fuel_filter", "category": "engine", "default_interval_km": 20000, "default_interval_days": 365, "priority": "high"},
                {"name": "Cabin Filter", "slug": "cabin_filter", "category": "engine", "default_interval_km": 15000, "default_interval_days": 365, "priority": "medium"},
                {"name": "Brake Pads", "slug": "brake_pads", "category": "brakes", "default_interval_km": 30000, "default_interval_days": 365, "priority": "critical"},
                {"name": "Brake Oil", "slug": "brake_oil", "category": "brakes", "default_interval_km": 40000, "default_interval_days": 730, "priority": "high"},
                {"name": "Coolant", "slug": "coolant", "category": "cooling", "default_interval_km": 50000, "default_interval_days": 730, "priority": "high"},
                {"name": "Battery", "slug": "battery", "category": "electrical", "default_interval_km": 50000, "default_interval_days": 1095, "priority": "high"},
                {"name": "Tyres", "slug": "tyres", "category": "tires", "default_interval_km": 40000, "default_interval_days": 1095, "priority": "critical"},
                {"name": "Tyre Rotation", "slug": "tyre_rotation", "category": "tires", "default_interval_km": 10000, "default_interval_days": 180, "priority": "medium"},
                {"name": "Wheel Alignment", "slug": "wheel_alignment", "category": "tires", "default_interval_km": 20000, "default_interval_days": 365, "priority": "medium"},
                {"name": "Gear Oil", "slug": "gear_oil", "category": "transmission", "default_interval_km": 40000, "default_interval_days": 730, "priority": "high"},
                {"name": "Transmission Oil", "slug": "transmission_oil", "category": "transmission", "default_interval_km": 60000, "default_interval_days": 1095, "priority": "high"},
                {"name": "Timing Belt", "slug": "timing_belt", "category": "engine", "default_interval_km": 100000, "default_interval_days": 1825, "priority": "critical"},
                {"name": "General Inspection", "slug": "general_inspection", "category": "inspection", "default_interval_km": 10000, "default_interval_days": 180, "priority": "medium"},
                {"name": "AC Service", "slug": "ac_service", "category": "hvac", "default_interval_km": 30000, "default_interval_days": 730, "priority": "medium"},
                {"name": "Suspension Check", "slug": "suspension_check", "category": "suspension", "default_interval_km": 40000, "default_interval_days": 730, "priority": "high"},
                {"name": "Electrical Inspection", "slug": "electrical_inspection", "category": "electrical", "default_interval_km": 50000, "default_interval_days": 1095, "priority": "medium"},
                {"name": "GPS Device Inspection", "slug": "gps_inspection", "category": "electronics", "default_interval_km": 0, "default_interval_days": 365, "priority": "medium"},
                {"name": "Tracker Health Check", "slug": "tracker_health", "category": "electronics", "default_interval_km": 0, "default_interval_days": 180, "priority": "medium"},
            ]
            # Use None for system/demo seeds to avoid FK issues in MySQL
            effective_cb = created_by if created_by and created_by > 0 else None
            for item in defaults:
                mt = MaintenanceType(
                    name=item["name"], slug=item["slug"], category=item["category"],
                    default_interval_km=item["default_interval_km"],
                    default_interval_days=item["default_interval_days"],
                    priority=item["priority"], is_system=item.get("is_system", False),
                    created_by=effective_cb
                )
                db.add(mt)
            await db.commit()
            return len(defaults)
        except Exception as e:
            logger.warning(f"DB error in seed_default_types: {e}")
            raise

    # ==================== MAINTENANCE RULES ====================

    @staticmethod
    async def get_maintenance_rules(db: AsyncSession, page: int = 1, page_size: int = 50,
                                     type_id: int = None, search: str = None,
                                     active_only: bool = None, sort_by: str = "rule_order",
                                     sort_order: str = "asc") -> Dict[str, Any]:
        try:
            query = select(MaintenanceRule).options(selectinload(MaintenanceRule.type))
            if type_id:
                query = query.where(MaintenanceRule.type_id == type_id)
            if search:
                query = query.where(or_(MaintenanceRule.name.ilike(f"%{search}%"),
                                         MaintenanceRule.description.ilike(f"%{search}%")))
            if active_only is not None:
                query = query.where(MaintenanceRule.is_active == active_only)

            total = (await db.execute(select(func.count()).select_from(MaintenanceRule))).scalar() or 0

            if sort_by == "rule_order":
                query = query.order_by(asc(MaintenanceRule.rule_order) if sort_order == "asc" else desc(MaintenanceRule.rule_order))
            elif sort_by == "name":
                query = query.order_by(asc(MaintenanceRule.name) if sort_order == "asc" else desc(MaintenanceRule.name))
            elif sort_by == "priority":
                query = query.order_by(asc(MaintenanceRule.priority) if sort_order == "asc" else desc(MaintenanceRule.priority))

            query = query.limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            rules = result.scalars().all()

            return {
                "items": [{"id": r.id, "type_id": r.type_id, "type_name": r.type.name if r.type else None,
                           "name": r.name, "description": r.description,
                           "trigger_km": r.trigger_km, "trigger_days": r.trigger_days,
                           "trigger_hours": r.trigger_hours, "trigger_manual": r.trigger_manual,
                           "grace_km": r.grace_km, "grace_days": r.grace_days,
                           "priority": r.priority, "rule_order": r.rule_order,
                           "min_interval_km": r.min_interval_km, "max_interval_km": r.max_interval_km,
                           "min_interval_days": r.min_interval_days, "max_interval_days": r.max_interval_days,
                           "is_active": r.is_active, "created_at": r.created_at.isoformat() if r.created_at else None,
                           "updated_at": r.updated_at.isoformat() if r.updated_at else None}
                          for r in rules],
                "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        except Exception as e:
            logger.warning(f"DB error in get_maintenance_rules: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    @staticmethod
    async def create_maintenance_rule(db: AsyncSession, data: Dict[str, Any], created_by: int = None) -> MaintenanceRule:
        try:
            type_id = data.get("type_id")
            if not type_id:
                raise ValueError("type_id is required")
            type_result = await db.execute(select(MaintenanceType).where(MaintenanceType.id == type_id))
            if not type_result.scalar_one_or_none():
                raise ValueError(f"Maintenance type with id {type_id} not found")
            rule = MaintenanceRule(
                type_id=type_id, name=data["name"], description=data.get("description"),
                trigger_km=data.get("trigger_km"), trigger_days=data.get("trigger_days"),
                trigger_hours=data.get("trigger_hours"), trigger_manual=data.get("trigger_manual", False),
                grace_km=data.get("grace_km", 0), grace_days=data.get("grace_days", 0),
                priority=data.get("priority", "medium"), rule_order=data.get("rule_order", 0),
                min_interval_km=data.get("min_interval_km"), max_interval_km=data.get("max_interval_km"),
                min_interval_days=data.get("min_interval_days"), max_interval_days=data.get("max_interval_days"),
                is_active=data.get("is_active", True), created_by=created_by
            )
            db.add(rule)
            await db.commit()
            await db.refresh(rule)
            return rule
        except Exception as e:
            logger.warning(f"DB error in create_maintenance_rule: {e}")
            raise

    @staticmethod
    async def update_maintenance_rule(db: AsyncSession, rule_id: int, data: Dict[str, Any], updated_by: int = None) -> Optional[MaintenanceRule]:
        try:
            result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                return None
            for field in ["name", "description", "trigger_km", "trigger_days", "trigger_hours",
                           "trigger_manual", "grace_km", "grace_days", "priority", "rule_order",
                           "min_interval_km", "max_interval_km", "min_interval_days", "max_interval_days", "is_active"]:
                if field in data:
                    setattr(rule, field, data[field])
            rule.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(rule)
            return rule
        except Exception as e:
            logger.warning(f"DB error in update_maintenance_rule: {e}")
            raise

    @staticmethod
    async def delete_maintenance_rule(db: AsyncSession, rule_id: int) -> bool:
        try:
            result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.id == rule_id))
            rule = result.scalar_one_or_none()
            if not rule:
                return False
            await db.delete(rule)
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in delete_maintenance_rule: {e}")
            raise

    # ==================== VALIDATION ====================

    @staticmethod
    def validate_rule(data: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        trigger_km = data.get("trigger_km")
        trigger_days = data.get("trigger_days")
        trigger_hours = data.get("trigger_hours")
        trigger_manual = data.get("trigger_manual", False)

        if not trigger_manual and not trigger_km and not trigger_days and not trigger_hours:
            errors.append("At least one trigger method (KM, Days, Hours) must be specified, or Manual must be enabled")

        if trigger_km is not None and trigger_km <= 0:
            errors.append("Trigger KM must be a positive number")
        if trigger_days is not None and trigger_days <= 0:
            errors.append("Trigger Days must be a positive number")
        if trigger_hours is not None and trigger_hours <= 0:
            errors.append("Trigger Hours must be a positive number")

        type_slug = data.get("type_slug") or data.get("slug")
        if type_slug and type_slug in MaintenancePlannerService.VALIDATION:
            v = MaintenancePlannerService.VALIDATION[type_slug]
            if trigger_km is not None:
                if trigger_km < v["min_km"]:
                    errors.append(f"KM interval ({trigger_km}) below minimum ({v['min_km']}) for {type_slug}")
                if trigger_km > v["max_km"]:
                    errors.append(f"KM interval ({trigger_km}) exceeds maximum ({v['max_km']}) for {type_slug}")
            if trigger_days is not None:
                if trigger_days < v["min_days"]:
                    errors.append(f"Days interval ({trigger_days}) below minimum ({v['min_days']}) for {type_slug}")
                if trigger_days > v["max_days"]:
                    errors.append(f"Days interval ({trigger_days}) exceeds maximum ({v['max_days']}) for {type_slug}")

        if data.get("grace_km") is not None and data["grace_km"] < 0:
            errors.append("Grace KM cannot be negative")
        if data.get("grace_days") is not None and data["grace_days"] < 0:
            errors.append("Grace Days cannot be negative")

        return {"valid": len(errors) == 0, "errors": errors}

    # ==================== TEMPLATES ====================

    @staticmethod
    async def get_templates(db: AsyncSession, page: int = 1, page_size: int = 50,
                             search: str = None, vehicle_type: str = None,
                             category: str = None, status: str = None,
                             active_only: bool = None) -> Dict[str, Any]:
        try:
            query = select(MaintenanceTemplate).where(MaintenanceTemplate.is_deleted == False)
            if search:
                query = query.where(or_(MaintenanceTemplate.name.ilike(f"%{search}%"),
                                         MaintenanceTemplate.description.ilike(f"%{search}%")))
            if vehicle_type:
                query = query.where(MaintenanceTemplate.vehicle_type == vehicle_type)
            if category:
                query = query.where(MaintenanceTemplate.vehicle_category == category)
            if status == 'active':
                query = query.where(and_(MaintenanceTemplate.is_active == True, MaintenanceTemplate.is_archived == False))
            elif status == 'inactive':
                query = query.where(MaintenanceTemplate.is_active == False)
            elif status == 'archived':
                query = query.where(MaintenanceTemplate.is_archived == True)
            elif active_only is not None:
                query = query.where(MaintenanceTemplate.is_active == active_only)

            total_query = select(func.count()).select_from(MaintenanceTemplate).where(MaintenanceTemplate.is_deleted == False)
            total = (await db.execute(total_query)).scalar() or 0
            query = query.order_by(MaintenanceTemplate.created_at.desc()).limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            templates = result.scalars().all()

            # Count rules and vehicle usage per template
            items = []
            for t in templates:
                rule_count = len([r for r in (t.template_rules or []) if r.is_active])
                vehicle_count = len([p for p in (t.plans or []) if p.is_active])
                items.append({
                    "id": t.id, "name": t.name, "slug": t.slug, "description": t.description,
                    "vehicle_type": t.vehicle_type, "vehicle_category": t.vehicle_category,
                    "manufacturer": t.manufacturer, "model": t.model,
                    "year_from": t.year_from, "year_to": t.year_to,
                    "estimated_service_cost": t.estimated_service_cost,
                    "estimated_annual_maint": t.estimated_annual_maint,
                    "is_active": t.is_active, "is_archived": t.is_archived,
                    "is_deleted": t.is_deleted, "is_system": t.is_system,
                    "rule_count": rule_count, "vehicle_count": vehicle_count,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None
                })

            # Get distinct categories
            cat_result = await db.execute(select(MaintenanceTemplate.vehicle_category).where(
                and_(MaintenanceTemplate.vehicle_category.isnot(None), MaintenanceTemplate.is_deleted == False)
            ).distinct())
            categories = sorted(set(c[0] for c in cat_result.all() if c[0]))

            return {
                "items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                "categories": categories
            }
        except Exception as e:
            logger.warning(f"DB error in get_templates: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0, "categories": []}

    @staticmethod
    async def create_template(db: AsyncSession, data: Dict[str, Any], created_by: int = None) -> MaintenanceTemplate:
        try:
            existing = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.name == data.get("name"), MaintenanceTemplate.is_deleted == False)
            ))
            if existing.scalar_one_or_none():
                raise ValueError(f"Template with name '{data.get('name')}' already exists")
            slug = data.get("slug") or data["name"].lower().replace(" ", "_")
            template = MaintenanceTemplate(
                name=data["name"], slug=slug,
                description=data.get("description"),
                vehicle_type=data.get("vehicle_type"),
                vehicle_category=data.get("vehicle_category"),
                manufacturer=data.get("manufacturer"), model=data.get("model"),
                year_from=data.get("year_from"), year_to=data.get("year_to"),
                estimated_service_cost=data.get("estimated_service_cost"),
                estimated_annual_maint=data.get("estimated_annual_maint"),
                is_active=data.get("is_active", True), is_system=data.get("is_system", False),
                created_by=created_by
            )
            db.add(template)
            await db.commit()
            await db.refresh(template)
            return template
        except Exception as e:
            logger.warning(f"DB error in create_template: {e}")
            raise

    @staticmethod
    async def update_template(db: AsyncSession, template_id: int, data: Dict[str, Any], updated_by: int = None) -> Optional[MaintenanceTemplate]:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.id == template_id, MaintenanceTemplate.is_deleted == False)
            ))
            template = result.scalar_one_or_none()
            if not template or template.is_system:
                return None
            for field in ["name", "slug", "description", "vehicle_type", "vehicle_category",
                           "manufacturer", "model", "year_from", "year_to",
                           "estimated_service_cost", "estimated_annual_maint",
                           "is_active", "is_archived"]:
                if field in data:
                    setattr(template, field, data[field])
            template.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(template)
            return template
        except Exception as e:
            logger.warning(f"DB error in update_template: {e}")
            raise

    @staticmethod
    async def delete_template(db: AsyncSession, template_id: int) -> bool:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == template_id))
            template = result.scalar_one_or_none()
            if not template or template.is_system or template.is_deleted:
                return False
            template.is_deleted = True
            template.is_active = False
            template.updated_at = datetime.utcnow()
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in delete_template: {e}")
            raise

    async def restore_template(db: AsyncSession, template_id: int) -> bool:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == template_id))
            template = result.scalar_one_or_none()
            if not template or not template.is_deleted:
                return False
            template.is_deleted = False
            template.is_active = True
            template.updated_at = datetime.utcnow()
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in restore_template: {e}")
            raise

    @staticmethod
    async def activate_template(db: AsyncSession, template_id: int) -> bool:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.id == template_id, MaintenanceTemplate.is_deleted == False)
            ))
            template = result.scalar_one_or_none()
            if not template:
                return False
            template.is_active = True
            template.is_archived = False
            template.updated_at = datetime.utcnow()
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in activate_template: {e}")
            raise

    @staticmethod
    async def deactivate_template(db: AsyncSession, template_id: int) -> bool:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.id == template_id, MaintenanceTemplate.is_deleted == False)
            ))
            template = result.scalar_one_or_none()
            if not template:
                return False
            template.is_active = False
            template.updated_at = datetime.utcnow()
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in deactivate_template: {e}")
            raise

    @staticmethod
    async def duplicate_template(db: AsyncSession, template_id: int, created_by: int = None) -> Optional[MaintenanceTemplate]:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.id == template_id, MaintenanceTemplate.is_deleted == False)
            ))
            original = result.scalar_one_or_none()
            if not original:
                return None
            new_name = f"{original.name} (Copy)"
            new_slug = f"{original.slug}_copy_{int(datetime.utcnow().timestamp())}"
            template = MaintenanceTemplate(
                name=new_name, slug=new_slug,
                description=original.description,
                vehicle_type=original.vehicle_type,
                vehicle_category=original.vehicle_category,
                manufacturer=original.manufacturer, model=original.model,
                year_from=original.year_from, year_to=original.year_to,
                estimated_service_cost=original.estimated_service_cost,
                estimated_annual_maint=original.estimated_annual_maint,
                is_active=False, is_system=False, created_by=created_by
            )
            db.add(template)
            await db.flush()

            # Copy all active template rules
            links_result = await db.execute(
                select(TemplateRuleLink).where(and_(
                    TemplateRuleLink.template_id == template_id, TemplateRuleLink.is_active == True
                ))
            )
            for link in links_result.scalars().all():
                new_link = TemplateRuleLink(
                    template_id=template.id, rule_id=link.rule_id,
                    override_km=link.override_km, override_days=link.override_days,
                    override_hours=link.override_hours, override_priority=link.override_priority,
                    execution_order=link.execution_order, is_enabled=link.is_enabled,
                    created_by=created_by
                )
                db.add(new_link)

            await db.commit()
            await db.refresh(template)
            return template
        except Exception as e:
            logger.warning(f"DB error in duplicate_template: {e}")
            raise

    @staticmethod
    async def get_template_rules(db: AsyncSession, template_id: int) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(TemplateRuleLink)
                .options(selectinload(TemplateRuleLink.rule))
                .where(TemplateRuleLink.template_id == template_id)
                .where(TemplateRuleLink.is_active == True)
                .order_by(TemplateRuleLink.execution_order, TemplateRuleLink.id)
            )
            links = result.scalars().all()
            return [{"id": link.id, "template_id": link.template_id,
                     "rule_id": link.rule_id,
                     "is_enabled": link.is_enabled,
                     "execution_order": link.execution_order,
                     "override_km": link.override_km, "override_days": link.override_days,
                     "override_hours": link.override_hours, "override_priority": link.override_priority,
                     "rule": {
                         "id": link.rule.id, "type_id": link.rule.type_id,
                         "type_name": link.rule.type.name if link.rule.type else None,
                         "name": link.rule.name,
                         "trigger_km": link.rule.trigger_km, "trigger_days": link.rule.trigger_days,
                         "trigger_hours": link.rule.trigger_hours,
                         "grace_km": link.rule.grace_km, "grace_days": link.rule.grace_days,
                         "priority": link.rule.priority, "rule_order": link.rule.rule_order
                     }}
                    for link in links]
        except Exception as e:
            logger.warning(f"DB error in get_template_rules: {e}")
            return []

    @staticmethod
    async def add_rule_to_template(db: AsyncSession, template_id: int, rule_id: int,
                                     override_km: float = None, override_days: int = None,
                                     override_hours: float = None, override_priority: str = None,
                                     execution_order: int = None, is_enabled: bool = True,
                                     created_by: int = None) -> TemplateRuleLink:
        try:
            template_result = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.id == template_id, MaintenanceTemplate.is_deleted == False)
            ))
            if not template_result.scalar_one_or_none():
                raise ValueError(f"Template {template_id} not found")
            rule_result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.id == rule_id))
            if not rule_result.scalar_one_or_none():
                raise ValueError(f"Rule {rule_id} not found")
            existing = await db.execute(select(TemplateRuleLink).where(
                and_(TemplateRuleLink.template_id == template_id, TemplateRuleLink.rule_id == rule_id,
                     TemplateRuleLink.is_active == True)
            ))
            if existing.scalar_one_or_none():
                raise ValueError("Rule already linked to this template")
            if execution_order is None:
                max_order = await db.execute(
                    select(func.max(TemplateRuleLink.execution_order))
                    .where(TemplateRuleLink.template_id == template_id)
                )
                execution_order = (max_order.scalar() or 0) + 1
            link = TemplateRuleLink(
                template_id=template_id, rule_id=rule_id,
                override_km=override_km, override_days=override_days,
                override_hours=override_hours, override_priority=override_priority,
                execution_order=execution_order, is_enabled=is_enabled,
                created_by=created_by
            )
            db.add(link)
            await db.commit()
            await db.refresh(link)
            return link
        except Exception as e:
            logger.warning(f"DB error in add_rule_to_template: {e}")
            raise

    @staticmethod
    async def remove_rule_from_template(db: AsyncSession, template_id: int, rule_id: int) -> bool:
        try:
            result = await db.execute(select(TemplateRuleLink).where(
                and_(TemplateRuleLink.template_id == template_id, TemplateRuleLink.rule_id == rule_id)
            ))
            link = result.scalar_one_or_none()
            if not link:
                return False
            link.is_active = False
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in remove_rule_from_template: {e}")
            raise

    @staticmethod
    async def reorder_template_rules(db: AsyncSession, template_id: int, rule_ids: List[int]) -> bool:
        try:
            for idx, rule_id in enumerate(rule_ids):
                await db.execute(
                    update(TemplateRuleLink)
                    .where(and_(TemplateRuleLink.template_id == template_id, TemplateRuleLink.rule_id == rule_id))
                    .values(execution_order=idx)
                )
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in reorder_template_rules: {e}")
            raise

    @staticmethod
    async def get_template_detail(db: AsyncSession, template_id: int) -> Optional[Dict[str, Any]]:
        try:
            result = await db.execute(select(MaintenanceTemplate).where(
                and_(MaintenanceTemplate.id == template_id, MaintenanceTemplate.is_deleted == False)
            ))
            template = result.scalar_one_or_none()
            if not template:
                return None
            rules = await MaintenancePlannerService.get_template_rules(db, template_id)
            vehicles_result = await db.execute(
                select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.template_id == template_id)
            )
            vehicles = vehicles_result.scalars().all()
            vehicle_list = [{"id": v.id, "device_id": v.device_id, "name": v.name, "is_active": v.is_active}
                           for v in vehicles]
            return {
                "id": template.id, "name": template.name, "slug": template.slug,
                "description": template.description,
                "vehicle_type": template.vehicle_type, "vehicle_category": template.vehicle_category,
                "manufacturer": template.manufacturer, "model": template.model,
                "year_from": template.year_from, "year_to": template.year_to,
                "estimated_service_cost": template.estimated_service_cost,
                "estimated_annual_maint": template.estimated_annual_maint,
                "is_active": template.is_active, "is_archived": template.is_archived,
                "is_system": template.is_system,
                "rules": rules, "vehicle_count": len(vehicle_list),
                "vehicles": vehicle_list,
                "created_at": template.created_at.isoformat() if template.created_at else None,
                "updated_at": template.updated_at.isoformat() if template.updated_at else None
            }
        except Exception as e:
            logger.warning(f"DB error in get_template_detail: {e}")
            return None

    @staticmethod
    async def seed_default_templates(db: AsyncSession, created_by: int = None) -> int:
        try:
            existing = await db.execute(select(func.count()).select_from(MaintenanceTemplate))
            if existing.scalar() > 0:
                return 0
            defaults = [
                {"name": "Passenger Car", "slug": "passenger_car", "vehicle_category": "Car",
                 "description": "Standard maintenance for passenger cars", "is_system": True},
                {"name": "Delivery Van", "slug": "delivery_van", "vehicle_category": "Van",
                 "description": "Maintenance schedule for light delivery vans", "is_system": True},
                {"name": "Pickup", "slug": "pickup", "vehicle_category": "Pickup",
                 "description": "Standard pickup truck maintenance", "is_system": True},
                {"name": "Motorcycle", "slug": "motorcycle", "vehicle_category": "Motorcycle",
                 "description": "Motorcycle maintenance schedule", "is_system": True},
                {"name": "Oil Tanker", "slug": "oil_tanker", "vehicle_category": "Tanker",
                 "description": "Hazmat oil tanker maintenance with safety checks", "is_system": True},
                {"name": "Water Bowser", "slug": "water_bowser", "vehicle_category": "Tanker",
                 "description": "Water bowser/tanker preventive maintenance", "is_system": True},
                {"name": "Heavy Truck", "slug": "heavy_truck", "vehicle_category": "Truck",
                 "description": "Heavy-duty truck full maintenance program", "is_system": True},
                {"name": "Trailer", "slug": "trailer", "vehicle_category": "Trailer",
                 "description": "Trailer inspection and maintenance schedule", "is_system": True},
                {"name": "Generator", "slug": "generator", "vehicle_category": "Generator",
                 "description": "Standby generator maintenance schedule", "is_system": True},
                {"name": "Construction Equipment", "slug": "construction_equipment", "vehicle_category": "Heavy Equipment",
                 "description": "Heavy construction equipment maintenance", "is_system": True},
            ]
            for d in defaults:
                tmpl = MaintenanceTemplate(**d, created_by=created_by, is_active=True)
                db.add(tmpl)
            await db.commit()
            await MaintenancePlannerService.seed_default_rules(db, created_by)
            await MaintenancePlannerService.seed_default_template_rules(db, created_by)
            return len(defaults)
        except Exception as e:
            logger.warning(f"DB error in seed_default_templates: {e}")
            return 0

    @staticmethod
    async def seed_default_rules(db: AsyncSession, created_by: int = None) -> int:
        try:
            existing = await db.execute(select(func.count()).select_from(MaintenanceRule))
            if existing.scalar() > 0:
                return 0
            types_result = await db.execute(select(MaintenanceType))
            types_list = types_result.scalars().all()
            type_map = {t.slug: t.id for t in types_list}
            rules = [
                {"type_slug": "engine_oil", "name": "Engine Oil Change", "trigger_km": 5000, "trigger_days": 180, "priority": "critical", "rule_order": 1},
                {"type_slug": "oil_filter", "name": "Oil Filter Replacement", "trigger_km": 5000, "trigger_days": 180, "priority": "high", "rule_order": 2},
                {"type_slug": "air_filter", "name": "Air Filter Replacement", "trigger_km": 10000, "trigger_days": 365, "priority": "high", "rule_order": 3},
                {"type_slug": "fuel_filter", "name": "Fuel Filter Replacement", "trigger_km": 20000, "trigger_days": 365, "priority": "high", "rule_order": 4},
                {"type_slug": "cabin_filter", "name": "Cabin Air Filter", "trigger_km": 15000, "trigger_days": 365, "priority": "medium", "rule_order": 5},
                {"type_slug": "brake_pads", "name": "Brake Pads Inspection", "trigger_km": 30000, "trigger_days": 365, "priority": "critical", "rule_order": 6},
                {"type_slug": "brake_oil", "name": "Brake Fluid Change", "trigger_km": 40000, "trigger_days": 730, "priority": "high", "rule_order": 7},
                {"type_slug": "coolant", "name": "Coolant Flush", "trigger_km": 50000, "trigger_days": 730, "priority": "high", "rule_order": 8},
                {"type_slug": "battery", "name": "Battery Check", "trigger_km": 50000, "trigger_days": 1095, "priority": "high", "rule_order": 9},
                {"type_slug": "tyres", "name": "Tyre Inspection", "trigger_km": 40000, "trigger_days": 1095, "priority": "critical", "rule_order": 10},
                {"type_slug": "tyre_rotation", "name": "Tyre Rotation", "trigger_km": 10000, "trigger_days": 180, "priority": "medium", "rule_order": 11},
                {"type_slug": "wheel_alignment", "name": "Wheel Alignment", "trigger_km": 20000, "trigger_days": 365, "priority": "medium", "rule_order": 12},
                {"type_slug": "gear_oil", "name": "Gear Oil Change", "trigger_km": 40000, "trigger_days": 730, "priority": "high", "rule_order": 13},
                {"type_slug": "transmission_oil", "name": "Transmission Oil Change", "trigger_km": 60000, "trigger_days": 1095, "priority": "high", "rule_order": 14},
                {"type_slug": "timing_belt", "name": "Timing Belt Replacement", "trigger_km": 100000, "trigger_days": 1825, "priority": "critical", "rule_order": 15},
                {"type_slug": "general_inspection", "name": "General Inspection", "trigger_km": 10000, "trigger_days": 180, "priority": "medium", "rule_order": 16},
                {"type_slug": "ac_service", "name": "AC Service", "trigger_km": 30000, "trigger_days": 730, "priority": "medium", "rule_order": 17},
                {"type_slug": "suspension_check", "name": "Suspension Inspection", "trigger_km": 40000, "trigger_days": 730, "priority": "high", "rule_order": 18},
                {"type_slug": "electrical_inspection", "name": "Electrical Inspection", "trigger_km": 50000, "trigger_days": 1095, "priority": "medium", "rule_order": 19},
                {"type_slug": "gps_inspection", "name": "GPS Device Inspection", "trigger_days": 365, "priority": "medium", "rule_order": 20},
                {"type_slug": "tracker_health", "name": "Tracker Health Check", "trigger_days": 180, "priority": "medium", "rule_order": 21},
            ]
            effective_cb = created_by if created_by and created_by > 0 else None
            count = 0
            for r in rules:
                type_id = type_map.get(r["type_slug"])
                if not type_id:
                    continue
                rule = MaintenanceRule(
                    type_id=type_id, name=r["name"],
                    trigger_km=r.get("trigger_km"), trigger_days=r.get("trigger_days"),
                    priority=r.get("priority", "medium"), rule_order=r.get("rule_order", 0),
                    is_active=True, created_by=effective_cb
                )
                db.add(rule)
                count += 1
            await db.commit()
            return count
        except Exception as e:
            logger.warning(f"DB error in seed_default_rules: {e}")
            return 0

    @staticmethod
    async def seed_default_template_rules(db: AsyncSession, created_by: int = None) -> int:
        try:
            templates_result = await db.execute(
                select(MaintenanceTemplate).where(MaintenanceTemplate.is_deleted == False)
            )
            templates = templates_result.scalars().all()
            rules_result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.is_active == True))
            all_rules = rules_result.scalars().all()
            rule_by_name = {r.name: r for r in all_rules}
            category_rules_map = {
                "Car": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                         "Tyre Inspection", "Tyre Rotation", "Battery Check", "Coolant Flush", "Cabin Air Filter", "General Inspection"],
                "Van": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                         "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "AC Service", "General Inspection"],
                "Pickup": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                            "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "Wheel Alignment", "General Inspection"],
                "Motorcycle": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                "Tyre Inspection", "Battery Check", "Coolant Flush", "Timing Belt Replacement", "General Inspection", "Suspension Inspection"],
                "Tanker": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                            "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "General Inspection", "Suspension Inspection"],
                "Truck": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                           "Brake Fluid Change", "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "Timing Belt Replacement"],
                "Trailer": ["Brake Pads Inspection", "Brake Fluid Change", "Tyre Inspection", "Tyre Rotation",
                             "Wheel Alignment", "General Inspection", "Electrical Inspection", "Suspension Inspection"],
                "Generator": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Fuel Filter Replacement",
                               "Battery Check", "Coolant Flush", "General Inspection", "Electrical Inspection"],
                "Heavy Equipment": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                     "Tyre Inspection", "Battery Check", "Coolant Flush", "General Inspection", "Suspension Inspection", "Wheel Alignment"],
            }
            effective_cb = created_by if created_by and created_by > 0 else None
            count = 0
            for tmpl in templates:
                cat = tmpl.vehicle_category or "Car"
                rule_names = category_rules_map.get(cat, category_rules_map["Car"])
                existing_links = await db.execute(
                    select(func.count()).select_from(TemplateRuleLink).where(
                        and_(TemplateRuleLink.template_id == tmpl.id, TemplateRuleLink.is_active == True)
                    )
                )
                if existing_links.scalar() > 0:
                    continue
                order = 1
                for rule_name in rule_names:
                    rule = rule_by_name.get(rule_name)
                    if not rule:
                        continue
                    link = TemplateRuleLink(
                        template_id=tmpl.id, rule_id=rule.id,
                        execution_order=order, is_enabled=True, is_active=True,
                        created_by=effective_cb
                    )
                    db.add(link)
                    order += 1
                    count += 1
            await db.commit()
            return count
        except Exception as e:
            logger.warning(f"DB error in seed_default_template_rules: {e}")
            return 0

    @staticmethod
    async def ensure_all_templates_have_rules(db: AsyncSession, created_by: int = None) -> Dict[str, Any]:
        try:
            rules_count = await db.execute(select(func.count()).select_from(MaintenanceRule))
            if rules_count.scalar() == 0:
                await MaintenancePlannerService.seed_default_rules(db, created_by)
            templates_result = await db.execute(
                select(MaintenanceTemplate).where(MaintenanceTemplate.is_deleted == False)
            )
            templates = templates_result.scalars().all()
            auto_fixed = 0
            for tmpl in templates:
                link_count = await db.execute(
                    select(func.count()).select_from(TemplateRuleLink).where(
                        and_(TemplateRuleLink.template_id == tmpl.id, TemplateRuleLink.is_active == True)
                    )
                )
                if link_count.scalar() == 0:
                    rules_result = await db.execute(
                        select(MaintenanceRule).where(MaintenanceRule.is_active == True)
                    )
                    all_rules = rules_result.scalars().all()
                    rule_by_name = {r.name: r for r in all_rules}
                    category_rules_map = {
                        "Car": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                 "Tyre Inspection", "Tyre Rotation", "Battery Check", "Coolant Flush", "Cabin Air Filter", "General Inspection"],
                        "Van": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                 "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "AC Service", "General Inspection"],
                        "Pickup": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                    "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "Wheel Alignment", "General Inspection"],
                        "Motorcycle": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                        "Tyre Inspection", "Battery Check", "Coolant Flush", "Timing Belt Replacement", "General Inspection", "Suspension Inspection"],
                        "Tanker": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                    "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "General Inspection", "Suspension Inspection"],
                        "Truck": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                   "Brake Fluid Change", "Tyre Inspection", "Battery Check", "Coolant Flush", "Gear Oil Change", "Timing Belt Replacement"],
                        "Trailer": ["Brake Pads Inspection", "Brake Fluid Change", "Tyre Inspection", "Tyre Rotation",
                                     "Wheel Alignment", "General Inspection", "Electrical Inspection", "Suspension Inspection"],
                        "Generator": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Fuel Filter Replacement",
                                       "Battery Check", "Coolant Flush", "General Inspection", "Electrical Inspection"],
                        "Heavy Equipment": ["Engine Oil Change", "Oil Filter Replacement", "Air Filter Replacement", "Brake Pads Inspection",
                                             "Tyre Inspection", "Battery Check", "Coolant Flush", "General Inspection", "Suspension Inspection", "Wheel Alignment"],
                    }
                    effective_cb = created_by if created_by and created_by > 0 else None
                    cat = tmpl.vehicle_category or "Car"
                    rule_names = category_rules_map.get(cat, category_rules_map["Car"])
                    order = 1
                    for rule_name in rule_names:
                        rule = rule_by_name.get(rule_name)
                        if not rule:
                            continue
                        link = TemplateRuleLink(
                            template_id=tmpl.id, rule_id=rule.id,
                            execution_order=order, is_enabled=True, is_active=True,
                            created_by=effective_cb
                        )
                        db.add(link)
                        order += 1
                    auto_fixed += 1
            await db.commit()
            return {"auto_fixed": auto_fixed}
        except Exception as e:
            logger.warning(f"DB error in ensure_all_templates_have_rules: {e}")
            return {"auto_fixed": 0, "error": str(e)}

    @staticmethod
    async def validate_templates(db: AsyncSession) -> Dict[str, Any]:
        try:
            templates_result = await db.execute(
                select(MaintenanceTemplate).where(MaintenanceTemplate.is_deleted == False)
            )
            templates = templates_result.scalars().all()
            rules_result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.is_active == True))
            all_rules = rules_result.scalars().all()
            total_templates = len(templates)
            total_rules = len(all_rules)
            total_template_rules = 0
            templates_with_zero_rules = []
            templates_assigned = []
            duplicate_templates = []
            seen_names = {}
            errors = []
            for tmpl in templates:
                if tmpl.name in seen_names:
                    duplicate_templates.append(f"{tmpl.name} (id={tmpl.id} dup of id={seen_names[tmpl.name]})")
                else:
                    seen_names[tmpl.name] = tmpl.id
                link_count_result = await db.execute(
                    select(func.count()).select_from(TemplateRuleLink).where(
                        and_(TemplateRuleLink.template_id == tmpl.id, TemplateRuleLink.is_active == True)
                    )
                )
                link_count = link_count_result.scalar() or 0
                total_template_rules += link_count
                if link_count == 0:
                    templates_with_zero_rules.append(tmpl.name)
                plan_count_result = await db.execute(
                    select(func.count()).select_from(VehicleMaintenancePlan).where(
                        and_(VehicleMaintenancePlan.template_id == tmpl.id, VehicleMaintenancePlan.is_active == True)
                    )
                )
                plan_count = plan_count_result.scalar() or 0
                if plan_count > 0:
                    templates_assigned.append({"template": tmpl.name, "vehicles": plan_count})
            rule_names = [r.name for r in all_rules]
            seen_rules = {}
            duplicate_rules = []
            for rn in rule_names:
                if rn in seen_rules:
                    seen_rules[rn] += 1
                else:
                    seen_rules[rn] = 1
            for rn, cnt in seen_rules.items():
                if cnt > 1:
                    duplicate_rules.append(f"{rn} (x{cnt})")
            return {
                "total_templates": total_templates,
                "total_rules": total_rules,
                "total_template_rules": total_template_rules,
                "templates_with_zero_rules": templates_with_zero_rules,
                "templates_assigned_to_vehicles": templates_assigned,
                "duplicate_templates": duplicate_templates,
                "duplicate_rules": duplicate_rules,
                "errors": errors,
                "status": "PASS" if not templates_with_zero_rules and not duplicate_templates and not errors else "FIXED" if not templates_with_zero_rules else "ISSUES FOUND"
            }
        except Exception as e:
            logger.warning(f"DB error in validate_templates: {e}")
            return {"error": str(e), "status": "ERROR"}

    # ==================== VEHICLE MAINTENANCE PLANS ====================

    @staticmethod
    async def get_vehicle_plans(db: AsyncSession, device_id: int = None, page: int = 1,
                                 page_size: int = 50, active_only: bool = None) -> Dict[str, Any]:
        try:
            query = select(VehicleMaintenancePlan).options(selectinload(VehicleMaintenancePlan.template))
            if device_id:
                query = query.where(VehicleMaintenancePlan.device_id == device_id)
            if active_only is not None:
                query = query.where(VehicleMaintenancePlan.is_active == active_only)

            total = (await db.execute(select(func.count()).select_from(VehicleMaintenancePlan))).scalar() or 0
            query = query.limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            plans = result.scalars().all()

            return {
                "items": [{"id": p.id, "device_id": p.device_id, "template_id": p.template_id,
                           "template_name": p.template.name if p.template else None,
                           "name": p.name, "description": p.description, "is_active": p.is_active,
                           "created_at": p.created_at.isoformat() if p.created_at else None} for p in plans],
                "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        except Exception as e:
            logger.warning(f"DB error in get_vehicle_plans: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    @staticmethod
    async def create_vehicle_plan(db: AsyncSession, device_id: int, data: Dict[str, Any], assigned_by: int = None) -> VehicleMaintenancePlan:
        try:
            plan = VehicleMaintenancePlan(
                device_id=device_id, template_id=data.get("template_id"),
                name=data["name"], description=data.get("description"),
                is_active=data.get("is_active", True), assigned_by=assigned_by
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
            return plan
        except Exception as e:
            logger.warning(f"DB error in create_vehicle_plan: {e}")
            raise

    @staticmethod
    async def update_vehicle_plan(db: AsyncSession, plan_id: int, data: Dict[str, Any], updated_by: int = None) -> Optional[VehicleMaintenancePlan]:
        try:
            result = await db.execute(select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if not plan:
                return None
            for field in ["template_id", "name", "description", "is_active"]:
                if field in data:
                    setattr(plan, field, data[field])
            plan.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(plan)
            return plan
        except Exception as e:
            logger.warning(f"DB error in update_vehicle_plan: {e}")
            raise

    @staticmethod
    async def delete_vehicle_plan(db: AsyncSession, plan_id: int) -> bool:
        try:
            result = await db.execute(select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if not plan:
                return False
            await db.delete(plan)
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in delete_vehicle_plan: {e}")
            raise

    @staticmethod
    async def assign_template_to_vehicle(db: AsyncSession, device_id: int, template_id: int, assigned_by: int = None) -> VehicleMaintenancePlan:
        try:
            template_result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == template_id))
            template = template_result.scalar_one_or_none()
            if not template:
                raise ValueError(f"Template {template_id} not found")
            existing = await db.execute(select(VehicleMaintenancePlan).where(
                and_(VehicleMaintenancePlan.device_id == device_id, VehicleMaintenancePlan.is_active == True)
            ))
            all_plans = existing.scalars().all()
            plan = None
            for p in all_plans:
                if not p.template_id:
                    plan = p
                    break
            if plan:
                plan.template_id = template_id
                plan.name = f"{template.name} Plan"
                plan.description = f"Auto-assigned from template '{template.name}'"
                plan.updated_at = datetime.utcnow()
            else:
                plan_name = f"{template.name} Plan"
                plan = await MaintenancePlannerService.create_vehicle_plan(
                    db, device_id, {"name": plan_name, "template_id": template_id, "description": f"Auto-assigned from template '{template.name}'"}, assigned_by
                )
            template_rules = await MaintenancePlannerService.get_template_rules(db, template_id)
            for tr in template_rules:
                rule_data = tr["rule"]
                await MaintenancePlannerService.create_plan_rule_override(
                    db, plan.id, rule_data["id"], rule_data["type_id"],
                    override_km=tr.get("override_km"), override_days=tr.get("override_days"),
                    override_hours=tr.get("override_hours"), override_priority=tr.get("override_priority"),
                    reason=f"Copied from template '{template.name}'", created_by=assigned_by
                )
            await MaintenancePlannerService.log_activity_event(
                db, "template_assigned", f"Template '{template.name}' assigned to device {device_id}",
                template_id=template_id, plan_id=plan.id, changed_by=assigned_by
            )
            return plan
        except Exception as e:
            logger.warning(f"DB error in assign_template_to_vehicle: {e}")
            raise

    @staticmethod
    async def replace_template_on_vehicle(db: AsyncSession, device_id: int, template_id: int, assigned_by: int = None) -> VehicleMaintenancePlan:
        try:
            template_result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == template_id))
            template = template_result.scalar_one_or_none()
            if not template:
                raise ValueError(f"Template {template_id} not found")
            existing = await db.execute(select(VehicleMaintenancePlan).where(
                and_(VehicleMaintenancePlan.device_id == device_id, VehicleMaintenancePlan.is_active == True)
            ))
            all_plans = existing.scalars().all()
            old_plan = None
            for p in all_plans:
                if p.template_id:
                    old_plan = p
                    break
            if not old_plan and all_plans:
                old_plan = all_plans[0]
            if old_plan:
                await db.execute(
                    update(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.plan_id == old_plan.id).values(is_enabled=False)
                )
                old_plan.template_id = template_id
                old_plan.name = f"{template.name} Plan"
                old_plan.description = f"Replaced with template '{template.name}'"
                old_plan.updated_at = datetime.utcnow()
                plan = old_plan
            else:
                plan = await MaintenancePlannerService.create_vehicle_plan(
                    db, device_id, {"name": f"{template.name} Plan", "template_id": template_id,
                                    "description": f"Assigned from template '{template.name}'"}, assigned_by
                )
            template_rules = await MaintenancePlannerService.get_template_rules(db, template_id)
            for tr in template_rules:
                rule_data = tr["rule"]
                await MaintenancePlannerService.create_plan_rule_override(
                    db, plan.id, rule_data["id"], rule_data["type_id"],
                    override_km=tr.get("override_km"), override_days=tr.get("override_days"),
                    override_hours=tr.get("override_hours"), override_priority=tr.get("override_priority"),
                    reason=f"Replaced from template '{template.name}'", created_by=assigned_by
                )
            await db.commit()
            await db.refresh(plan)
            await MaintenancePlannerService.log_activity_event(
                db, "template_replaced", f"Template replaced with '{template.name}' on device {device_id}",
                template_id=template_id, plan_id=plan.id, changed_by=assigned_by
            )
            return plan
        except Exception as e:
            logger.warning(f"DB error in replace_template_on_vehicle: {e}")
            raise

    @staticmethod
    async def unassign_template(db: AsyncSession, plan_id: int) -> bool:
        try:
            result = await db.execute(select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if not plan:
                return False
            await db.execute(
                update(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.plan_id == plan_id).values(is_enabled=False)
            )
            plan.template_id = None
            plan.updated_at = datetime.utcnow()
            await db.commit()
            await MaintenancePlannerService.log_activity_event(
                db, "template_unassigned", f"Template unassigned from plan {plan_id}",
                plan_id=plan_id
            )
            return True
        except Exception as e:
            logger.warning(f"DB error in unassign_template: {e}")
            raise

    @staticmethod
    async def bulk_assign_template(db: AsyncSession, device_ids: List[int], template_id: int, assigned_by: int = None) -> Dict[str, Any]:
        try:
            template_result = await db.execute(select(MaintenanceTemplate).where(MaintenanceTemplate.id == template_id))
            template = template_result.scalar_one_or_none()
            if not template:
                raise ValueError(f"Template {template_id} not found")
            success = []
            failed = []
            for did in device_ids:
                try:
                    existing = await db.execute(select(VehicleMaintenancePlan).where(
                        and_(VehicleMaintenancePlan.device_id == did, VehicleMaintenancePlan.is_active == True)
                    ))
                    old_plan = existing.scalar_one_or_none()
                    if old_plan:
                        await db.execute(
                            update(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.plan_id == old_plan.id).values(is_enabled=False)
                        )
                        old_plan.template_id = template_id
                        old_plan.name = f"{template.name} Plan"
                        old_plan.description = f"Replaced with template '{template.name}'"
                        old_plan.updated_at = datetime.utcnow()
                        plan = old_plan
                    else:
                        plan = await MaintenancePlannerService.create_vehicle_plan(
                            db, did, {"name": f"{template.name} Plan", "template_id": template_id,
                                      "description": f"Assigned from template '{template.name}'"}, assigned_by
                        )
                    template_rules = await MaintenancePlannerService.get_template_rules(db, template_id)
                    for tr in template_rules:
                        rule_data = tr["rule"]
                        await MaintenancePlannerService.create_plan_rule_override(
                            db, plan.id, rule_data["id"], rule_data["type_id"],
                            override_km=tr.get("override_km"), override_days=tr.get("override_days"),
                            override_hours=tr.get("override_hours"), override_priority=tr.get("override_priority"),
                            reason=f"Bulk assigned from template '{template.name}'", created_by=assigned_by
                        )
                    success.append(did)
                except Exception as e:
                    failed.append({"device_id": did, "error": str(e)})
            await db.commit()
            return {"success": success, "failed": failed, "total": len(device_ids),
                    "template_name": template.name}
        except Exception as e:
            logger.warning(f"DB error in bulk_assign_template: {e}")
            raise

    @staticmethod
    async def validate_vehicle_plans(db: AsyncSession) -> Dict[str, Any]:
        try:
            plans_result = await db.execute(
                select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.is_active == True)
            )
            plans = plans_result.scalars().all()
            total_plans = len(plans)
            plans_with_template = 0
            plans_without_template = 0
            total_overrides = 0
            plans_missing_overrides = []
            errors = []
            for p in plans:
                if p.template_id:
                    plans_with_template += 1
                else:
                    plans_without_template += 1
                override_count = await db.execute(
                    select(func.count()).select_from(VehiclePlanRuleOverride).where(
                        and_(VehiclePlanRuleOverride.plan_id == p.id, VehiclePlanRuleOverride.is_enabled == True)
                    )
                )
                cnt = override_count.scalar() or 0
                total_overrides += cnt
                if p.template_id and cnt == 0:
                    plans_missing_overrides.append(f"Plan {p.id} (device {p.device_id})")
            return {
                "total_plans": total_plans,
                "plans_with_template": plans_with_template,
                "plans_without_template": plans_without_template,
                "total_overrides": total_overrides,
                "plans_missing_overrides": plans_missing_overrides,
                "errors": errors,
                "status": "PASS" if not plans_missing_overrides and not errors else "ISSUES FOUND"
            }
        except Exception as e:
            logger.warning(f"DB error in validate_vehicle_plans: {e}")
            return {"error": str(e), "status": "ERROR"}

    # ==================== VEHICLES WITH PLANS ====================

    @staticmethod
    async def get_vehicles_with_plans(db: AsyncSession, search: str = None, status: str = None,
                                      health: str = None, category: str = None,
                                      page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        try:
            tc = await get_traccar_client()
            devices = await tc.get_devices()
            positions = await tc.get_positions() or []
            pos_map = {p.get("deviceId"): p for p in positions} if positions else {}

            plan_result = await db.execute(
                select(VehicleMaintenancePlan).options(selectinload(VehicleMaintenancePlan.template))
            )
            plans_db = plan_result.scalars().all()
            plans_by_device = {p.device_id: p for p in plans_db}

            items = []
            for d in (devices or []):
                did = d.get("id")
                pos = pos_map.get(did)
                attrs = (pos.get("attributes", {}) or {}) if pos else {}
                total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
                current_km = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)

                plan = plans_by_device.get(did)

                template_name = None
                plan_status = "No Plan"
                plan_id = None
                plan_is_active = False
                health_status = "healthy"
                next_service_km = None
                next_service_days = None
                last_service_km = None
                last_service_date = None
                overdue_count = 0
                due_soon_count = 0

                if plan:
                    template_name = plan.template.name if plan.template else None
                    plan_status = "Active" if plan.is_active else "Inactive"
                    plan_id = plan.id
                    plan_is_active = plan.is_active
                    try:
                        calc = await MaintenancePlannerService.get_vehicle_due_calculation(db, did)
                        if calc.get("items"):
                            items_list = calc["items"]
                            overdue_count = sum(1 for i in items_list if i["overall_status"] == "overdue")
                            due_soon_count = sum(1 for i in items_list if i["overall_status"] == "due_soon")
                            healthy_count = sum(1 for i in items_list if i["overall_status"] == "healthy")
                            if overdue_count > 0:
                                health_status = "overdue"
                            elif due_soon_count > 0:
                                health_status = "due_soon"
                            else:
                                health_status = "healthy"
                            next_service_km = min((i["km_remaining"] for i in items_list if i["km_remaining"] is not None), default=None)
                            next_service_days = min((i["days_remaining"] for i in items_list if i["days_remaining"] is not None), default=None)
                    except Exception:
                        pass

                    try:
                        log_result = await db.execute(
                            select(MaintenanceLog).where(MaintenanceLog.device_id == did)
                            .order_by(MaintenanceLog.service_date.desc()).limit(1)
                        )
                        last_log = log_result.scalar_one_or_none()
                        if last_log:
                            last_service_km = last_log.service_value
                            last_service_date = last_log.service_date.isoformat() if last_log.service_date else None
                    except Exception:
                        pass

                item = {
                    "id": did, "name": d.get("name"), "uniqueId": d.get("uniqueId"),
                    "status": d.get("status"), "category": d.get("category"),
                    "model": d.get("model"), "phone": d.get("phone"),
                    "current_km": current_km if current_km > 0 else None,
                    "plan_id": plan_id, "plan_name": plan.name if plan else None,
                    "plan_status": plan_status, "plan_is_active": plan_is_active,
                    "plan_created_at": plan.created_at.isoformat() if plan and plan.created_at else None,
                    "template_name": template_name, "template_id": plan.template_id if plan else None,
                    "template_updated_at": plan.template.updated_at.isoformat() if plan and plan.template and plan.template.updated_at else None,
                    "health_status": health_status,
                    "next_service_km": next_service_km, "next_service_days": next_service_days,
                    "last_service_km": last_service_km, "last_service_date": last_service_date,
                    "overdue_count": overdue_count, "due_soon_count": due_soon_count,
                    "latitude": pos.get("latitude") if pos else None,
                    "longitude": pos.get("longitude") if pos else None,
                    "speed": pos.get("speed") if pos else 0,
                    "lastUpdate": d.get("lastUpdate"),
                }
                items.append(item)

            if search:
                sl = search.lower()
                items = [i for i in items if sl in (i["name"] or "").lower() or sl in (i["uniqueId"] or "").lower()]
            if status and status != "all":
                items = [i for i in items if i["plan_status"].lower() == status.lower()]
            if health and health != "all":
                items = [i for i in items if i["health_status"].lower() == health.lower()]
            if category and category != "all":
                items = [i for i in items if (i["category"] or "").lower() == category.lower()]

            total = len(items)
            start = (page - 1) * page_size
            items = items[start:start + page_size]

            categories = sorted(set(i["category"] for i in items if i["category"]))

            return {
                "items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                "categories": categories
            }
        except Exception as e:
            logger.warning(f"Error in get_vehicles_with_plans: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0, "categories": []}

    # ==================== RULE OVERRIDE ====================

    @staticmethod
    async def get_plan_overrides(db: AsyncSession, plan_id: int) -> List[Dict[str, Any]]:
        try:
            result = await db.execute(
                select(VehiclePlanRuleOverride)
                .options(selectinload(VehiclePlanRuleOverride.rule), selectinload(VehiclePlanRuleOverride.type))
                .where(VehiclePlanRuleOverride.plan_id == plan_id)
            )
            overrides = result.scalars().all()
            return [{"id": o.id, "plan_id": o.plan_id, "rule_id": o.rule_id, "rule_name": o.rule.name if o.rule else None,
                     "type_id": o.type_id, "type_name": o.type.name if o.type else None,
                     "override_km": o.override_km, "override_days": o.override_days,
                     "override_hours": o.override_hours, "override_priority": o.override_priority,
                     "is_enabled": o.is_enabled, "reason": o.reason,
                     "created_at": o.created_at.isoformat() if o.created_at else None,
                     "updated_at": o.updated_at.isoformat() if o.updated_at else None}
                    for o in overrides]
        except Exception as e:
            logger.warning(f"DB error in get_plan_overrides: {e}")
            return []

    @staticmethod
    async def create_plan_rule_override(db: AsyncSession, plan_id: int, rule_id: int, type_id: int,
                                          override_km: float = None, override_days: int = None,
                                          override_hours: float = None, override_priority: str = None,
                                          is_enabled: bool = True, reason: str = None,
                                          created_by: int = None) -> VehiclePlanRuleOverride:
        try:
            plan_result = await db.execute(select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.id == plan_id))
            if not plan_result.scalar_one_or_none():
                raise ValueError(f"Plan {plan_id} not found")
            rule_result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.id == rule_id))
            if not rule_result.scalar_one_or_none():
                raise ValueError(f"Rule {rule_id} not found")
            existing = await db.execute(select(VehiclePlanRuleOverride).where(
                and_(VehiclePlanRuleOverride.plan_id == plan_id, VehiclePlanRuleOverride.rule_id == rule_id,
                     VehiclePlanRuleOverride.is_enabled == True)
            ))
            if existing.scalar_one_or_none():
                raise ValueError("Rule already overridden for this plan")
            override = VehiclePlanRuleOverride(
                plan_id=plan_id, rule_id=rule_id, type_id=type_id,
                override_km=override_km, override_days=override_days,
                override_hours=override_hours, override_priority=override_priority,
                is_enabled=is_enabled, reason=reason, created_by=created_by
            )
            db.add(override)
            await db.commit()
            await db.refresh(override)
            return override
        except Exception as e:
            logger.warning(f"DB error in create_plan_rule_override: {e}")
            raise

    @staticmethod
    async def update_plan_override(db: AsyncSession, override_id: int, data: Dict[str, Any], updated_by: int = None) -> Optional[VehiclePlanRuleOverride]:
        try:
            result = await db.execute(select(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.id == override_id))
            override = result.scalar_one_or_none()
            if not override:
                return None
            for field in ["override_km", "override_days", "override_hours", "override_priority", "is_enabled", "reason"]:
                if field in data:
                    setattr(override, field, data[field])
            override.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(override)
            return override
        except Exception as e:
            logger.warning(f"DB error in update_plan_override: {e}")
            raise

    @staticmethod
    async def delete_plan_override(db: AsyncSession, override_id: int) -> bool:
        try:
            result = await db.execute(select(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.id == override_id))
            override = result.scalar_one_or_none()
            if not override:
                return False
            await db.delete(override)
            await db.commit()
            return True
        except Exception as e:
            logger.warning(f"DB error in delete_plan_override: {e}")
            raise

    # ==================== DUE CALCULATION ENGINE ====================

    @staticmethod
    async def get_vehicle_due_calculation(db: AsyncSession, device_id: int) -> Dict[str, Any]:
        try:
            current_km = 0.0
            try:
                tc = await get_traccar_client()
                positions = await tc.get_device_positions(device_id)
                if positions:
                    pos = positions[0]
                    attrs = pos.get("attributes", {}) or {}
                    total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
                    if total_dist > 0:
                        current_km = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)
            except Exception:
                pass

            plan_result = await db.execute(
                select(VehicleMaintenancePlan).where(and_(
                    VehicleMaintenancePlan.device_id == device_id, VehicleMaintenancePlan.is_active == True
                ))
            )
            plan = plan_result.scalars().first()

            overrides = {}
            if plan:
                ov_result = await db.execute(
                    select(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.plan_id == plan.id)
                )
                for ov in ov_result.scalars().all():
                    overrides[ov.rule_id] = ov

            if plan and plan.template_id:
                template_rules = await MaintenancePlannerService.get_template_rules(db, plan.template_id)
                rules = []
                for tr in template_rules:
                    rule_data = tr["rule"]
                    override = overrides.get(rule_data["id"])
                    rules.append({
                        "rule_id": rule_data["id"], "type_id": rule_data["type_id"],
                        "type_name": rule_data["type_name"], "rule_name": rule_data["name"],
                        "trigger_km": override.override_km if override and override.override_km is not None else rule_data["trigger_km"],
                        "trigger_days": override.override_days if override and override.override_days is not None else rule_data["trigger_days"],
                        "trigger_hours": override.override_hours if override and override.override_hours is not None else rule_data["trigger_hours"],
                        "grace_km": rule_data["grace_km"], "grace_days": rule_data["grace_days"],
                        "priority": override.override_priority if override and override.override_priority else rule_data["priority"],
                        "is_enabled": override.is_enabled if override and override is not None else True,
                    })
            else:
                rules_result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.is_active == True))
                rules_db = rules_result.scalars().all()
                rules = []
                for r in rules_db:
                    override = overrides.get(r.id)
                    rules.append({
                        "rule_id": r.id, "type_id": r.type_id,
                        "trigger_km": override.override_km if override and override.override_km is not None else r.trigger_km,
                        "trigger_days": override.override_days if override and override.override_days is not None else r.trigger_days,
                        "trigger_hours": override.override_hours if override and override.override_hours is not None else r.trigger_hours,
                        "grace_km": r.grace_km, "grace_days": r.grace_days,
                        "priority": override.override_priority if override and override.override_priority else r.priority,
                        "is_enabled": override.is_enabled if override else True,
                    })

            # Calculate due status for each rule
            items = []
            for rule in rules:
                if not rule["is_enabled"]:
                    continue
                km_interval = rule["trigger_km"]
                days_interval = rule["trigger_days"]
                hours_interval = rule["trigger_hours"]
                grace_km = rule["grace_km"] or 0
                grace_days = rule["grace_days"] or 0

                km_status = None
                days_status = None

                if km_interval:
                    km_remaining = km_interval - current_km
                    km_status = "overdue" if km_remaining <= -grace_km else ("due_soon" if km_remaining <= grace_km else "healthy")

                if days_interval:
                    last_service_date = await MaintenancePlannerService._get_last_service_date(db, device_id)
                    if last_service_date:
                        due_date = last_service_date + timedelta(days=days_interval)
                        days_remaining = (due_date - datetime.utcnow()).days
                        days_status = "overdue" if days_remaining <= -grace_days else ("due_soon" if days_remaining <= grace_days else "healthy")
                    else:
                        days_status = "no_history"

                if km_status == "overdue" or days_status == "overdue":
                    overall = "overdue"
                elif km_status == "due_soon" or days_status == "due_soon":
                    overall = "due_soon"
                elif km_status == "no_history" or days_status == "no_history":
                    overall = "no_history"
                else:
                    overall = "healthy"

                items.append({
                    "rule_id": rule["rule_id"], "type_id": rule["type_id"],
                    "type_name": rule["type_name"], "rule_name": rule["rule_name"],
                    "current_km": current_km,
                    "km_interval": km_interval, "km_remaining": round((km_interval - current_km), 2) if km_interval else None,
                    "days_interval": days_interval, "days_remaining": days_remaining if days_interval else None,
                    "hours_interval": hours_interval,
                    "overall_status": overall,
                    "priority": rule["priority"],
                    "km_status": km_status, "days_status": days_status
                })

            return {
                "device_id": device_id, "current_km": current_km, "plan_name": plan.name if plan else None,
                "items": items,
                "summary": {
                    "total": len(items), "overdue": sum(1 for i in items if i["overall_status"] == "overdue"),
                    "due_soon": sum(1 for i in items if i["overall_status"] == "due_soon"),
                    "healthy": sum(1 for i in items if i["overall_status"] == "healthy"),
                    "no_history": sum(1 for i in items if i["overall_status"] == "no_history")
                }
            }
        except Exception as e:
            logger.warning(f"DB error in get_vehicle_due_calculation: {e}")
            return {"device_id": device_id, "current_km": 0, "plan_name": None, "items": [], "summary": {"total": 0, "overdue": 0, "due_soon": 0, "healthy": 0, "no_history": 0}}

    @staticmethod
    async def _get_last_service_date(db: AsyncSession, device_id: int) -> Optional[datetime]:
        try:
            result = await db.execute(
                select(VehicleMaintenance.last_service_date)
                .where(VehicleMaintenance.device_id == device_id)
                .order_by(VehicleMaintenance.last_service_date.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.warning(f"DB error in _get_last_service_date: {e}")
            return None

    # ==================== PRIORITY ENGINE ====================

    @staticmethod
    def calculate_priority(km_remaining: float = None, days_remaining: int = None,
                             km_grace: float = 0, days_grace: int = 0,
                             interval_km: float = None, interval_days: int = None) -> Dict[str, Any]:
        priority = "normal"
        label = "Normal"

        if km_remaining is not None and km_remaining < 0:
            abs_km = abs(km_remaining)
            if abs_km > (interval_km or 5000) * 0.5 or abs_km > 5000:
                priority = "critical"
                label = "Critical"
            elif abs_km > (interval_km or 5000) * 0.2:
                priority = "overdue"
                label = "Overdue"
            elif km_remaining <= km_grace:
                priority = "upcoming"
                label = "Due Soon"
            else:
                priority = "normal"
                label = "Normal"

        if days_remaining is not None and days_remaining < 0:
            abs_days = abs(days_remaining)
            if abs_days > (interval_days or 180) * 0.5 or abs_days > 90:
                if priority != "critical":
                    priority = "critical"
                    label = "Critical"
            elif abs_days > 14:
                if priority not in ("critical", "overdue"):
                    priority = "overdue"
                    label = "Overdue"
            elif days_remaining <= days_grace:
                if priority not in ("critical", "overdue", "upcoming"):
                    priority = "upcoming"
                    label = "Due Soon"
            else:
                if priority == "normal" and not label or label == "Normal":
                    priority = "normal"
                    label = "Normal"

        return {"priority": priority, "label": label}

    # ==================== RULE HISTORY ====================

    @staticmethod
    async def get_rule_history(db: AsyncSession, rule_id: int = None, type_id: int = None,
                                template_id: int = None, plan_id: int = None,
                                page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        try:
            query = select(RuleHistory).order_by(desc(RuleHistory.created_at))
            if rule_id:
                query = query.where(RuleHistory.rule_id == rule_id)
            if type_id:
                query = query.where(RuleHistory.type_id == type_id)
            if template_id:
                query = query.where(RuleHistory.template_id == template_id)
            if plan_id:
                query = query.where(RuleHistory.plan_id == plan_id)

            total = (await db.execute(select(func.count()).select_from(RuleHistory))).scalar() or 0
            query = query.limit(page_size).offset((page - 1) * page_size)
            result = await db.execute(query)
            history = result.scalars().all()

            return {
                "items": [{"id": h.id, "rule_id": h.rule_id, "type_id": h.type_id,
                           "template_id": h.template_id, "plan_id": h.plan_id,
                           "field_name": h.field_name, "old_value": h.old_value,
                           "new_value": h.new_value, "changed_by": h.changed_by,
                           "reason": h.reason, "created_at": h.created_at.isoformat() if h.created_at else None}
                          for h in history],
                "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        except Exception as e:
            logger.warning(f"DB error in get_rule_history: {e}")
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

    @staticmethod
    async def add_rule_history(db: AsyncSession, rule_id: int = None, type_id: int = None,
                                 template_id: int = None, plan_id: int = None,
                                 field_name: str = None, old_value: str = None,
                                 new_value: str = None, changed_by: int = None,
                                 reason: str = None) -> RuleHistory:
        try:
            entry = RuleHistory(
                rule_id=rule_id, type_id=type_id, template_id=template_id, plan_id=plan_id,
                field_name=field_name, old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                changed_by=changed_by, reason=reason
            )
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            return entry
        except Exception as e:
            logger.warning(f"DB error in add_rule_history: {e}")
            raise

    # ==================== SMART DUE ENGINE ====================

    _fleet_cache = None
    _fleet_cache_ts = None
    _FLEET_CACHE_TTL = 300

    @classmethod
    async def calculate_fleet_due_status(cls, db: AsyncSession, force: bool = False) -> Dict[str, Any]:
        now = datetime.utcnow()
        if not force and cls._fleet_cache and cls._fleet_cache_ts and (now - cls._fleet_cache_ts).total_seconds() < cls._FLEET_CACHE_TTL:
            return cls._fleet_cache

        tc = await get_traccar_client()
        devices = await tc.get_devices()
        if not devices:
            return {"vehicles": [], "summary": {"total": 0, "overdue": 0, "due_soon": 0, "healthy": 0, "no_plan": 0}, "health_score": 0, "calculated_at": now.isoformat()}

        positions = await tc.get_positions()
        pos_map = {}
        for p in (positions or []):
            did = p.get("deviceId")
            attrs = p.get("attributes", {}) or {}
            total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
            pos_map[did] = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)

        plan_result = await db.execute(select(VehicleMaintenancePlan).where(VehicleMaintenancePlan.is_active == True))
        plans_map = {p.device_id: p for p in plan_result.scalars().all()}

        all_plan_ids = list(set(p.id for p in plans_map.values()))
        overrides_by_plan = {}
        if all_plan_ids:
            ov_result = await db.execute(select(VehiclePlanRuleOverride).where(VehiclePlanRuleOverride.plan_id.in_(all_plan_ids)))
            for ov in ov_result.scalars().all():
                overrides_by_plan.setdefault(ov.plan_id, {})[ov.rule_id] = ov

        type_result = await db.execute(select(MaintenanceType).where(MaintenanceType.is_deleted == False))
        type_map = {t.id: t for t in type_result.scalars().all()}

        rule_result = await db.execute(select(MaintenanceRule).where(MaintenanceRule.is_active == True))
        all_rules = {r.id: r for r in rule_result.scalars().all()}

        template_ids = set(p.template_id for p in plans_map.values() if p.template_id)
        template_rules_cache = {}
        for tid in template_ids:
            template_rules_cache[tid] = await cls.get_template_rules(db, tid)

        last_service_dates = {}
        try:
            ls_result = await db.execute(
                select(VehicleMaintenance.device_id, func.max(VehicleMaintenance.last_service_date).label("last_date"))
                .where(VehicleMaintenance.last_service_date.isnot(None))
                .group_by(VehicleMaintenance.device_id)
            )
            for row in ls_result.all():
                last_service_dates[row.device_id] = row.last_date
        except Exception:
            pass

        vehicles = []
        for device in devices:
            did = device.get("id")
            name = device.get("name", str(did))
            current_km = pos_map.get(did, 0)
            plan = plans_map.get(did)
            overrides = overrides_by_plan.get(plan.id, {}) if plan else {}

            effective_rules = []
            if plan and plan.template_id and plan.template_id in template_rules_cache:
                for tr in template_rules_cache[plan.template_id]:
                    rd = tr["rule"]
                    ov = overrides.get(rd["id"])
                    _t_obj = type_map.get(rd["type_id"])
                    _t_name = rd.get("type_name") or (_t_obj.name if _t_obj else "Unknown")
                    effective_rules.append({
                        "rule_id": rd["id"], "type_id": rd["type_id"],
                        "type_name": _t_name,
                        "rule_name": rd.get("name", "Rule"),
                        "trigger_km": ov.override_km if ov and ov.override_km is not None else rd["trigger_km"],
                        "trigger_days": ov.override_days if ov and ov.override_days is not None else rd["trigger_days"],
                        "trigger_hours": ov.override_hours if ov and ov.override_hours is not None else rd["trigger_hours"],
                        "grace_km": rd.get("grace_km", 0) or 0,
                        "grace_days": rd.get("grace_days", 0) or 0,
                        "priority": (ov.override_priority if ov and ov.override_priority else None) or rd.get("priority", "medium"),
                        "is_enabled": ov.is_enabled if ov else tr.get("is_enabled", True),
                    })
            elif not plan:
                for rid, r in all_rules.items():
                    _t_obj2 = type_map.get(r.type_id)
                    effective_rules.append({
                        "rule_id": r.id, "type_id": r.type_id,
                        "type_name": _t_obj2.name if _t_obj2 else "Unknown",
                        "rule_name": r.name,
                        "trigger_km": r.trigger_km, "trigger_days": r.trigger_days,
                        "trigger_hours": r.trigger_hours,
                        "grace_km": r.grace_km or 0, "grace_days": r.grace_days or 0,
                        "priority": r.priority, "is_enabled": True,
                    })

            items = []
            for rule in effective_rules:
                if not rule["is_enabled"]:
                    continue

                km_interval = rule["trigger_km"]
                days_interval = rule["trigger_days"]
                grace_km = rule["grace_km"] or 0
                grace_days = rule["grace_days"] or 0
                km_status = None
                days_status = None
                km_remaining = None
                days_remaining = None
                next_due_date = None

                if km_interval:
                    km_remaining = km_interval - current_km
                    km_status = "overdue" if km_remaining <= -grace_km else ("due_soon" if km_remaining <= grace_km else "healthy")

                if days_interval:
                    lsd = last_service_dates.get(did)
                    if lsd:
                        due_dt = lsd + timedelta(days=days_interval)
                        days_remaining = (due_dt - now).days
                        next_due_date = due_dt.isoformat()
                        days_status = "overdue" if days_remaining <= -grace_days else ("due_soon" if days_remaining <= grace_days else "healthy")
                    else:
                        days_status = "no_history"

                if km_status == "overdue" or days_status == "overdue":
                    overall = "overdue"
                elif km_status == "due_soon" or days_status == "due_soon":
                    overall = "due_soon"
                elif km_status == "no_history" or days_status == "no_history":
                    overall = "no_history"
                else:
                    overall = "healthy"

                items.append({
                    "rule_id": rule["rule_id"], "type_id": rule["type_id"],
                    "type_name": rule["type_name"], "rule_name": rule["rule_name"],
                    "current_km": current_km, "km_interval": km_interval,
                    "km_remaining": round(km_remaining, 2) if km_remaining is not None else None,
                    "days_interval": days_interval, "days_remaining": days_remaining,
                    "next_due_date": next_due_date,
                    "overall_status": overall, "priority": rule["priority"],
                    "km_status": km_status, "days_status": days_status,
                })

            overdue_c = sum(1 for i in items if i["overall_status"] == "overdue")
            due_soon_c = sum(1 for i in items if i["overall_status"] == "due_soon")
            critical_c = sum(1 for i in items if i["overall_status"] == "overdue" and i["priority"] == "critical")

            if critical_c > 0:
                v_status = "critical"
            elif overdue_c > 0:
                v_status = "overdue"
            elif due_soon_c > 0:
                v_status = "warning"
            else:
                v_status = "healthy"

            vehicles.append({
                "device_id": did, "vehicle_name": name, "current_km": current_km,
                "plan_name": plan.name if plan else None, "template_id": plan.template_id if plan else None,
                "overall_status": v_status, "items": items,
                "summary": {"total": len(items), "overdue": overdue_c, "due_soon": due_soon_c,
                            "healthy": sum(1 for i in items if i["overall_status"] == "healthy"),
                            "no_history": sum(1 for i in items if i["overall_status"] == "no_history")}
            })

        total_v = len(vehicles)
        total_overdue = sum(1 for v in vehicles if v["overall_status"] in ("overdue", "critical"))
        total_due_soon = sum(1 for v in vehicles if v["overall_status"] == "warning")
        total_healthy = sum(1 for v in vehicles if v["overall_status"] == "healthy")
        total_no_plan = sum(1 for v in vehicles if v["plan_name"] is None)
        health_score = round((total_healthy / total_v) * 100) if total_v > 0 else 0

        result = {
            "vehicles": vehicles,
            "summary": {"total": total_v, "overdue": total_overdue, "due_soon": total_due_soon,
                        "healthy": total_healthy, "no_plan": total_no_plan},
            "health_score": health_score,
            "calculated_at": now.isoformat(),
        }
        cls._fleet_cache = result
        cls._fleet_cache_ts = now
        return result

    @classmethod
    async def get_upcoming_items(cls, db: AsyncSession, page: int = 1, page_size: int = 20,
                                  search: str = None, type_filter: str = None,
                                  sort_by: str = "days_remaining", sort_order: str = "asc") -> Dict[str, Any]:
        fleet = await cls.calculate_fleet_due_status(db)
        all_items = []
        for v in fleet.get("vehicles", []):
            for item in v["items"]:
                if item["overall_status"] in ("healthy", "due_soon", "no_history"):
                    all_items.append({
                        "vehicle_id": v["device_id"], "vehicle_name": v["vehicle_name"],
                        "current_km": v["current_km"], "plan_name": v["plan_name"],
                        "type_name": item["type_name"], "rule_name": item["rule_name"],
                        "km_interval": item["km_interval"], "km_remaining": item["km_remaining"],
                        "days_interval": item["days_interval"], "days_remaining": item["days_remaining"],
                        "next_due_date": item["next_due_date"],
                        "priority": item["priority"], "overall_status": item["overall_status"],
                    })

        if search:
            s = search.lower()
            all_items = [i for i in all_items if s in i["vehicle_name"].lower() or s in (i["type_name"] or "").lower() or s in (i["rule_name"] or "").lower()]
        if type_filter:
            all_items = [i for i in all_items if i["type_name"] == type_filter]

        rev = sort_order == "desc"
        if sort_by == "days_remaining":
            all_items.sort(key=lambda x: x["days_remaining"] if x["days_remaining"] is not None else 99999, reverse=rev)
        elif sort_by == "km_remaining":
            all_items.sort(key=lambda x: x["km_remaining"] if x["km_remaining"] is not None else 99999, reverse=rev)
        elif sort_by == "vehicle_name":
            all_items.sort(key=lambda x: x["vehicle_name"], reverse=rev)
        elif sort_by == "priority":
            p_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            all_items.sort(key=lambda x: p_order.get(x["priority"], 99), reverse=rev)

        total = len(all_items)
        start = (page - 1) * page_size
        items = all_items[start:start + page_size]
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size}

    @classmethod
    async def get_overdue_items(cls, db: AsyncSession, page: int = 1, page_size: int = 20,
                                 search: str = None, sort_by: str = "days_remaining",
                                 sort_order: str = "asc") -> Dict[str, Any]:
        fleet = await cls.calculate_fleet_due_status(db)
        all_items = []
        for v in fleet.get("vehicles", []):
            for item in v["items"]:
                if item["overall_status"] == "overdue":
                    abs_days = abs(item["days_remaining"]) if item["days_remaining"] is not None else 0
                    abs_km = abs(item["km_remaining"]) if item["km_remaining"] is not None else 0
                    if abs_days > 30 or abs_km > 1000:
                        risk = "Critical"
                    elif abs_days > 14 or abs_km > 500:
                        risk = "High"
                    elif abs_days > 7 or abs_km > 200:
                        risk = "Medium"
                    else:
                        risk = "Low"
                    all_items.append({
                        "vehicle_id": v["device_id"], "vehicle_name": v["vehicle_name"],
                        "current_km": v["current_km"], "plan_name": v["plan_name"],
                        "type_name": item["type_name"], "rule_name": item["rule_name"],
                        "km_interval": item["km_interval"], "km_remaining": item["km_remaining"],
                        "days_interval": item["days_interval"], "days_remaining": item["days_remaining"],
                        "next_due_date": item["next_due_date"],
                        "priority": item["priority"], "risk_level": risk,
                        "km_overdue": abs_km, "days_overdue": abs_days,
                    })

        if search:
            s = search.lower()
            all_items = [i for i in all_items if s in i["vehicle_name"].lower() or s in (i["type_name"] or "").lower()]

        risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        all_items.sort(key=lambda x: (risk_order.get(x["risk_level"], 99), -x["days_overdue"]))

        total = len(all_items)
        start = (page - 1) * page_size
        items = all_items[start:start + page_size]
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size}

    @classmethod
    async def get_calendar_events(cls, db: AsyncSession, year: int, month: int) -> List[Dict[str, Any]]:
        fleet = await cls.calculate_fleet_due_status(db)
        events = []
        for v in fleet.get("vehicles", []):
            for item in v["items"]:
                if item.get("next_due_date"):
                    try:
                        dt = datetime.fromisoformat(item["next_due_date"])
                        if dt.year == year and dt.month == month:
                            events.append({
                                "day": dt.day, "date": item["next_due_date"],
                                "vehicle_id": v["device_id"], "vehicle_name": v["vehicle_name"],
                                "type_name": item["type_name"], "rule_name": item["rule_name"],
                                "priority": item["priority"],
                                "is_overdue": item["overall_status"] == "overdue",
                            })
                    except Exception:
                        pass
        return events

    @classmethod
    async def get_activity_feed(cls, db: AsyncSession, limit: int = 50) -> List[Dict[str, Any]]:
        activities = []
        try:
            hist_result = await db.execute(
                select(RuleHistory).order_by(desc(RuleHistory.created_at)).limit(limit)
            )
            for h in hist_result.scalars().all():
                activities.append({
                    "id": h.id, "type": "rule_change",
                    "description": f"Rule field '{h.field_name}' changed from '{h.old_value}' to '{h.new_value}'",
                    "rule_id": h.rule_id, "template_id": h.template_id, "plan_id": h.plan_id,
                    "changed_by": h.changed_by, "reason": h.reason,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                })
        except Exception as e:
            logger.warning(f"Error fetching rule history for activity: {e}")

        try:
            log_result = await db.execute(
                select(MaintenanceLog).order_by(desc(MaintenanceLog.created_at)).limit(limit)
            )
            for log in log_result.scalars().all():
                activities.append({
                    "id": log.id, "type": "service_log",
                    "description": f"{log.service_type.replace('_', ' ').title()} — odometer {log.service_value}",
                    "device_id": log.device_id, "schedule_id": log.schedule_id,
                    "cost": log.cost, "technician": log.technician,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                })
        except Exception as e:
            logger.warning(f"Error fetching maintenance logs for activity: {e}")

        activities.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return activities[:limit]

    @classmethod
    async def recalculate_fleet(cls, db: AsyncSession) -> Dict[str, Any]:
        result = await cls.calculate_fleet_due_status(db, force=True)
        return {
            "message": "Fleet recalculated",
            "summary": result["summary"],
            "health_score": result["health_score"],
            "calculated_at": result["calculated_at"],
            "vehicle_count": len(result["vehicles"]),
        }

    @classmethod
    async def recalculate_vehicle(cls, db: AsyncSession, device_id: int) -> Dict[str, Any]:
        tc = await get_traccar_client()
        current_km = 0.0
        try:
            positions = await tc.get_device_positions(device_id)
            if positions:
                attrs = positions[0].get("attributes", {}) or {}
                total_dist = attrs.get("totalDistance") or attrs.get("odometer") or 0
                current_km = round(total_dist / 1000, 2) if total_dist > 1000 else round(total_dist, 2)
        except Exception:
            pass

        plan_result = await db.execute(select(VehicleMaintenancePlan).where(and_(
            VehicleMaintenancePlan.device_id == device_id, VehicleMaintenancePlan.is_active == True)))
        plan = plan_result.scalar_one_or_none()

        cls._fleet_cache = None
        cls._fleet_cache_ts = None
        await cls.calculate_fleet_due_status(db, force=True)

        return {"device_id": device_id, "current_km": current_km, "plan_id": plan.id if plan else None, "message": "Vehicle recalculated"}

    @staticmethod
    async def log_activity_event(db: AsyncSession, event_type: str, description: str,
                                   rule_id: int = None, type_id: int = None, template_id: int = None,
                                   plan_id: int = None, changed_by: int = None, reason: str = None):
        try:
            entry = RuleHistory(
                rule_id=rule_id, type_id=type_id, template_id=template_id, plan_id=plan_id,
                field_name=event_type, old_value=None, new_value=description,
                changed_by=changed_by, reason=reason,
            )
            db.add(entry)
            await db.commit()
        except Exception as e:
            logger.warning(f"Error logging activity: {e}")


maintenance_planner_service = MaintenancePlannerService()