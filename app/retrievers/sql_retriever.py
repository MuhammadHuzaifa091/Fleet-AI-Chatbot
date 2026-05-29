from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from app.models.traccar import Device, Position, Event, Maintenance, UserDevice
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class SQLRetriever:
    def __init__(self, db: AsyncSession, current_user: Dict[str, Any]):
        self.db = db
        self.current_user = current_user

    def _apply_rbac(self, query):
        """Applies Role-Based Access Control to SQLAlchemy queries"""
        if self.current_user.get("role") in ["SUPERADMIN", "ADMIN"]:
            return query
            
        # USER: strict tc_user_device filter
        return query.join(UserDevice, UserDevice.deviceid == Device.id).where(UserDevice.userid == self.current_user["id"])

    async def get_live_vehicles(self, limit: int = 1000) -> List[Dict[str, Any]]:
        # LEFT JOIN: show vehicles even without a position record
        query = select(Device, Position).outerjoin(Position, Device.positionid == Position.id).where(Device.disabled == False)
        query = self._apply_rbac(query).limit(limit)
        
        result = await self.db.execute(query)
        data = []
        
        for device, position in result.all():
            dev_attr = device.attributes or {}
            pos_attr = position.attributes if position else {}
            
            # --- REAL DATA ONLY --- no mocks, no fake calculations ---
            
            # VIN: native DB column has priority over attributes
            vin        = getattr(device, 'vin', None) or pos_attr.get("vin") or dev_attr.get("vin") or pos_attr.get("vehicleId") or None
            vin_source = getattr(device, 'vin_source', None)  # 'obd' | 'manual' | None

            # Fuel: only real sensor data, None if not available
            fuel_level = pos_attr.get("fuelLevel") or pos_attr.get("fuel") or None

            # Battery: only real sensor data
            battery = pos_attr.get("battery") or pos_attr.get("batteryLevel") or pos_attr.get("power") or None

            data.append({
                "id":            device.id,
                "name":          device.name,
                "uniqueId":      device.uniqueid,
                "status":        device.status,
                "lastUpdate":    device.lastupdate,
                "groupId":       device.groupid,
                "category":      device.category,
                "model":         getattr(device, 'model', None) or dev_attr.get("model") or None,
                "contact":       device.contact,
                "phone":         device.phone,
                "latitude":      position.latitude  if position else None,
                "longitude":     position.longitude if position else None,
                "altitude":      position.altitude  if position else None,
                "speed":         position.speed     if position else 0,
                "course":        position.course    if position else 0,
                "address":       position.address   if position else None,
                "protocol":      position.protocol  if position else None,
                "valid":         position.valid      if position else False,
                "attributes":    pos_attr,
                "device_attributes": dev_attr,
                "vin":           vin,
                "vin_source":    vin_source,
                "fuelLevel":     fuel_level,
                "batteryLevel":  battery,
                "make":          getattr(device, 'manufacturer', None) or dev_attr.get("make") or None,
                "year":          getattr(device, 'year', None) or dev_attr.get("year") or None,
            })
        return data


    async def get_vehicle_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        query = select(Device, Position).outerjoin(Position, Device.positionid == Position.id).where(Device.name.ilike(f"%{name}%"))
        query = self._apply_rbac(query)
        result = await self.db.execute(query)
        row = result.first()
        if row:
            device, position = row
            return {
                "id": device.id,
                "name": device.name,
                "uniqueId": device.uniqueid,
                "status": device.status,
                "latitude": position.latitude if position else 0,
                "longitude": position.longitude if position else 0,
                "speed": position.speed if position else 0,
                "attributes": position.attributes if position else {}
            }
        return None

    async def get_overspeed_events(self, days: int = 1) -> List[Dict[str, Any]]:
        since = datetime.utcnow() - timedelta(days=days)
        query = select(Event, Device).join(Device, Event.deviceid == Device.id).where(
            Event.type == "deviceOverspeed",
            Event.eventtime >= since
        )
        # Apply RBAC to events via device relationship
        if self.current_user["role"] != "SUPERADMIN":
             query = query.join(UserDevice, UserDevice.deviceid == Device.id).where(UserDevice.userid == self.current_user["id"])
             
        result = await self.db.execute(query)
        return [{"device": row.Device.name, "time": row.Event.eventtime, "attributes": row.Event.attributes} for row in result.all()]

    async def get_maintenance_status(self) -> List[Dict[str, Any]]:
        query = select(Maintenance)
        result = await self.db.execute(query)
        return [{"id": m.id, "name": m.name, "type": m.type, "start": m.start, "period": m.period} for m in result.scalars().all()]

    async def execute_custom_query(self, query_str: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(text(query_str))
        return [dict(row) for row in result.mappings().all()]

    async def update_vehicle(self, device_id: int, data: Dict[str, Any]) -> bool:
        """Updates vehicle details in tc_devices"""
        query = select(Device).where(Device.id == device_id)
        query = self._apply_rbac(query)
        result = await self.db.execute(query)
        device = result.scalar_one_or_none()
        
        if not device:
            return False
            
        # Update allowed fields
        if "name" in data: device.name = data["name"]
        if "uniqueid" in data: device.uniqueid = data["uniqueid"]
        if "vin" in data: 
            # VIN might be in attributes or a separate column if we added it
            # Traccar usually stores it in attributes, but we can store it in attributes here
            current_attr = device.attributes or {}
            current_attr["vin"] = data["vin"]
            device.attributes = current_attr
        if "model" in data: device.model = data["model"]
        if "category" in data: device.category = data["category"]
        if "groupId" in data: device.groupid = data["groupId"]
        if "contact" in data: device.contact = data["contact"]
        if "phone" in data: device.phone = data["phone"]
        
        # Merge attributes if provided
        if "attributes" in data:
            current_attr = device.attributes or {}
            current_attr.update(data["attributes"])
            device.attributes = current_attr
            
        await self.db.commit()
        return True
