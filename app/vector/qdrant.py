import asyncio
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from app.embeddings.service import embedding_service
from typing import List, Dict, Any, Optional

class QdrantService:
    def __init__(self):
        try:
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY,
                timeout=5
            )
            self.client.get_collections()
            print(f"Connected to Qdrant server at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        except Exception as e:
            print(f"Failed to connect to Qdrant server: {e}")
            print("Falling back to Qdrant Local Mode (In-memory)")
            self.client = QdrantClient(location=":memory:")

        self.collection_name = "fleet_intelligence"
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
                )
        except Exception as e:
            print(f"Failed to connect to Qdrant: {e}. Semantic search is disabled.")

    def _sync_search(self, query_vector, limit):
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )

    def _sync_upsert(self, points):
        self.client.upsert(collection_name=self.collection_name, points=points)

    async def upsert_points(self, points: List[Dict[str, Any]]):
        qdrant_points = []
        for p in points:
            vector = embedding_service.generate_embeddings(p["text"])[0]
            qdrant_points.append(
                models.PointStruct(id=p["id"], vector=vector, payload={"text": p["text"], **p.get("metadata", {})})
            )
        await asyncio.to_thread(self._sync_upsert, qdrant_points)

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            query_vector = embedding_service.generate_embeddings(query)[0]
            hits = await asyncio.to_thread(self._sync_search, query_vector, limit)
            return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in hits]
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return []

qdrant_service = QdrantService()
