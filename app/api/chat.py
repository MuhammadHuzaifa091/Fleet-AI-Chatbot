from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.rag.pipeline import RAGPipeline
from app.memory.redis_memory import redis_memory
from app.api.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import Request
from app.core.limiter import limiter

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str
    intent: str
    context_sources: Optional[List[str]] = None

@router.post("/", response_model=ChatResponse)
@limiter.limit("5/minute")
async def chat_endpoint(
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        # Add current timestamp to user context for time-aware queries
        current_user["now"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Get History
        history = await redis_memory.get_history(request.session_id)
        
        # 2. Run Pipeline
        pipeline = RAGPipeline(db, current_user)
        result = await pipeline.process_query(request.query, history)
        
        # 3. Save to History
        await redis_memory.add_message(request.session_id, "user", request.query)
        await redis_memory.add_message(request.session_id, "assistant", result["answer"])
        
        return ChatResponse(
            answer=result["answer"],
            intent=result["intent"],
            context_sources=result.get("context_sources", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
