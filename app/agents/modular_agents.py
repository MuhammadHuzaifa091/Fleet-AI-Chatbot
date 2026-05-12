from app.retrievers.sql_retriever import SQLRetriever
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

class SQLAgent:
    def __init__(self, db: AsyncSession):
        self.retriever = SQLRetriever(db)

    async def get_vehicle_status(self, name: str) -> Dict[str, Any]:
        return await self.retriever.get_vehicle_by_name(name)

class TelemetryAgent:
    def __init__(self, db: AsyncSession):
        self.retriever = SQLRetriever(db)

    async def analyze_overspeeding(self) -> List[Dict[str, Any]]:
        return await self.retriever.get_overspeed_events()

class MaintenanceAgent:
    def __init__(self, db: AsyncSession):
        self.retriever = SQLRetriever(db)

    async def get_alerts(self) -> List[Dict[str, Any]]:
        return await self.retriever.get_maintenance_status()
