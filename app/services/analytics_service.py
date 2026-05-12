from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    async def get_analytics_summary(db: AsyncSession, user_id: int, role: str) -> Dict[str, Any]:
        params = {"uid": user_id} if role == "USER" else {}
        join_clause = "JOIN tc_user_device ud ON d.id = ud.deviceid AND ud.userid = :uid" if role == "USER" else ""

        async def fetch_scalar(query: str) -> int:
            try:
                result = await db.execute(text(query), params)
                return result.scalar() or 0
            except Exception: return 0

        async def fetch_all(query: str) -> List[Dict]:
            try:
                result = await db.execute(text(query), params)
                return [dict(row._mapping) for row in result.all()]
            except Exception as e:
                logger.error(f"List fetch error: {e}")
                return []

        # 1. KPIs
        total = await fetch_scalar(f"SELECT COUNT(*) FROM tc_devices d {join_clause}")
        
        # Status Subquery
        # Use simple temporal filtering for performance
        status_table = f"""
            SELECT d.id, d.name, p.speed, p.devicetime, p.servertime 
            FROM tc_devices d 
            {join_clause} 
            JOIN tc_positions p ON d.positionid = p.id
        """
        
        active = await fetch_scalar(f"SELECT COUNT(*) FROM ({status_table}) s WHERE s.devicetime >= NOW() - INTERVAL 5 MINUTE")
        idle = await fetch_scalar(f"SELECT COUNT(*) FROM ({status_table}) s WHERE s.speed = 0 AND s.devicetime >= NOW() - INTERVAL 30 MINUTE")
        stale = await fetch_scalar(f"SELECT COUNT(*) FROM tc_devices d {join_clause} WHERE lastupdate < NOW() - INTERVAL 1 DAY OR lastupdate IS NULL")
        overspeed = await fetch_scalar(f"SELECT COUNT(*) FROM ({status_table}) s WHERE s.speed > 80")
        
        # 2. Recent Events (Last 5)
        # Try both servertime and eventtime fallback
        recent_events = []
        try:
            recent_events = await fetch_all(f"""
                SELECT e.id, d.name as device_name, e.type, e.eventtime as time
                FROM tc_events e
                JOIN tc_devices d ON e.deviceid = d.id
                {join_clause.replace('d.id', 'e.deviceid')}
                ORDER BY e.id DESC LIMIT 5
            """)
        except Exception:
             recent_events = await fetch_all(f"""
                SELECT e.id, d.name as device_name, e.type, e.servertime as time
                FROM tc_events e
                JOIN tc_devices d ON e.deviceid = d.id
                {join_clause.replace('d.id', 'e.deviceid')}
                ORDER BY e.id DESC LIMIT 5
            """)

        # 3. Aggregates (Distance and Maintenance)
        try:
            # Get maintenance alerts (upcoming or overdue)
            maintenance_alerts = await fetch_all(f"""
                SELECT m.name, d.name as device_name, m.type, m.period
                FROM tc_maintenances m
                JOIN tc_device_maintenance dm ON m.id = dm.maintenanceid
                JOIN tc_devices d ON dm.deviceid = d.id
                {join_clause}
                LIMIT 3
            """)
        except Exception:
            maintenance_alerts = []

        # 4. System Health
        db_size = await fetch_scalar("SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) FROM information_schema.tables WHERE table_schema = DATABASE()")

        return {
            "kpis": {
                "total": int(total),
                "active": int(active),
                "idle": int(idle),
                "stale": int(stale),
                "overspeed": int(overspeed)
            },
            "recentEvents": recent_events,
            "maintenanceAlerts": maintenance_alerts,
            "systemHealth": {
                "dbSizeMb": float(db_size or 0),
                "serverTime": datetime.now().strftime("%H:%M:%S")
            }
        }
