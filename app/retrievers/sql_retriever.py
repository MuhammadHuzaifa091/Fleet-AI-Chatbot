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
        if self.current_user["role"] == "SUPERADMIN":
            return query
            
        elif self.current_user["role"] == "ADMIN":
            # For simplicity, if Admin has specific groups, we would filter by groupid here
            # Assuming ADMIN means full org access but not super admin. 
            pass # Apply org/group filters in real impl
            
        # USER -> strict tc_user_device filter
        return query.join(UserDevice, UserDevice.deviceid == Device.id).where(UserDevice.userid == self.current_user["id"])

    async def get_live_vehicles(self) -> List[Dict[str, Any]]:
        query = select(Device, Position).join(Position, Device.positionid == Position.id).where(Device.disabled == False)
        query = self._apply_rbac(query)
        
        result = await self.db.execute(query)
        data = []
        
        def decode_vin_demo(vin: str) -> Dict[str, str]:
            if not vin or len(vin) < 3: return {"make": "Unknown", "model": "Generic", "year": "N/A"}
            wmi = vin[:3].upper()
            make_map = {"1HG": "Honda", "1NX": "Toyota", "1VW": "Volkswagen", "3FA": "Ford", "WAU": "Audi", "WBA": "BMW", "1G1": "Chevrolet", "KM8": "Hyundai", "WP0": "Porsche", "JHM": "Honda"}
            make = make_map.get(wmi, "Toyota") # Fallback to Toyota
            model_map = {"Honda": "Civic", "Toyota": "Corolla", "Volkswagen": "Golf", "Ford": "F-150", "Audi": "A4", "BMW": "3 Series", "Chevrolet": "Silverado", "Hyundai": "Tucson", "Porsche": "911"}
            model = model_map.get(make, "Standard")
            
            # 10th char generally indicates year
            year_char = vin[9] if len(vin) >= 10 else "N"
            year = "2022" if year_char.isalpha() else "2019"
            
            return {"make": make, "model": model, "year": year}
            
        import hashlib
        
        for device, position in result.all():
            dev_attr = device.attributes or {}
            pos_attr = position.attributes or {}
            
            # Attempt to extract VIN
            vin = pos_attr.get("vin") or dev_attr.get("vin") or pos_attr.get("vehicleId")
            
            # For demonstration, if no real VIN is available, generate a consistent one based on ID
            is_mock_vin = False
            if not vin:
                is_mock_vin = True
                hashed = hashlib.md5(str(device.id).encode()).hexdigest().upper()
                wmi_choices = ["1HG", "1NX", "1VW", "3FA", "WAU", "WBA"]
                wmi = wmi_choices[device.id % len(wmi_choices)]
                vin = f"{wmi}{hashed[:5]}{device.id % 9}{hashed[-5:]}Z"
            
            decoded = decode_vin_demo(vin)
            
            data.append({
                "id": device.id,
                "name": device.name,
                "uniqueId": device.uniqueid,
                "status": device.status,
                "lastUpdate": device.lastupdate,
                "latitude": position.latitude,
                "longitude": position.longitude,
                "speed": position.speed,
                "address": position.address,
                "attributes": pos_attr,
                "device_attributes": dev_attr,
                "vin": vin,
                "vin_mocked": is_mock_vin,
                "make": decoded["make"],
                "model": decoded["model"],
                "year": decoded["year"]
            })
        return data

    async def get_vehicle_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        query = select(Device, Position).join(Position, Device.positionid == Position.id).where(Device.name.ilike(f"%{name}%"))
        result = await self.db.execute(query)
        row = result.first()
        if row:
            device, position = row
            return {
                "id": device.id,
                "name": device.name,
                "uniqueId": device.uniqueid,
                "status": device.status,
                "latitude": position.latitude,
                "longitude": position.longitude,
                "speed": position.speed,
                "attributes": position.attributes
            }
        return None

    async def get_overspeed_events(self, days: int = 1) -> List[Dict[str, Any]]:
        since = datetime.utcnow() - timedelta(days=days)
        query = select(Event, Device).join(Device, Event.deviceid == Device.id).where(
            Event.type == "deviceOverspeed",
            Event.servertime >= since
        )
        result = await self.db.execute(query)
        return [{"device": row.Device.name, "time": row.Event.servertime, "attributes": row.Event.attributes} for row in result.all()]

    async def get_maintenance_status(self) -> List[Dict[str, Any]]:
        query = select(Maintenance)
        result = await self.db.execute(query)
        return [{"id": m.id, "name": m.name, "type": m.type, "start": m.start, "period": m.period} for m in result.scalars().all()]

    async def execute_custom_query(self, query_str: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(text(query_str))
        return [dict(row) for row in result.mappings().all()]
