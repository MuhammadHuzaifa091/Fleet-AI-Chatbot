from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from app.embeddings.service import embedding_service
from typing import List, Dict, Any, Optional

class QdrantService:
    def __init__(self):
        try:
            # Try to connect to the remote/docker Qdrant server
            self.client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                api_key=settings.QDRANT_API_KEY,
                timeout=5
            )
            # Test connection immediately
            self.client.get_collections()
            print(f"Connected to Qdrant server at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        except Exception as e:
            print(f"Failed to connect to Qdrant server: {e}")
            print("Falling back to Qdrant Local Mode (In-memory/Disk)")
            # Path for local storage
            import os
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
                    vectors_config=models.VectorParams(
                        size=384, # Size for all-MiniLM-L6-v2
                        distance=models.Distance.COSINE
                    )
                )
        except Exception as e:
            print(f"Failed to connect to Qdrant: {e}. Semantic search is disabled.")

    async def upsert_points(self, points: List[Dict[str, Any]]):
        """
        Points should be a list of dicts with:
        id: int/uuid
        text: str (to be embedded)
        metadata: dict
        """
        qdrant_points = []
        for p in points:
            vector = embedding_service.generate_embeddings(p["text"])[0]
            qdrant_points.append(
                models.PointStruct(
                    id=p["id"],
                    vector=vector,
                    payload={"text": p["text"], **p.get("metadata", {})}
                )
            )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points
        )

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            query_vector = embedding_service.generate_embeddings(query)[0]
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            return [{"id": hit.id, "score": hit.score, "payload": hit.payload} for hit in hits]
        except Exception as e:
            print(f"Qdrant search failed: {e}")
            return []

qdrant_service = QdrantService()
