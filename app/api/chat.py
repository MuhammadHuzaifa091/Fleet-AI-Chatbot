from fastapi import APIRouter, Depends, Query, Body, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, update, delete
from app.db.session import get_db, SessionLocal
from app.models.chat import ChatSession, ChatMessage
from app.rag.pipeline import RAGPipeline
from app.api.auth import get_current_user
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import asyncio
import uuid
from loguru import logger

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    chat_id: Optional[int] = None # Database ID of the chat session

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """List all chat sessions for the current user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_email == current_user["email"])
        .order_by(desc(ChatSession.updated_at))
    )
    sessions = result.scalars().all()
    return sessions

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new chat session."""
    new_session = ChatSession(
        user_email=current_user["email"],
        title="New Conversation"
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return new_session

@router.get("/{chat_id}/messages")
async def get_chat_messages(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get all messages for a specific session."""
    # Verify ownership
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_email == current_user["email"])
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == chat_id).order_by(ChatMessage.timestamp)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages]

@router.delete("/{chat_id}")
async def delete_chat_session(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a chat session."""
    result = await db.execute(
        delete(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_email == current_user["email"])
    )
    await db.commit()
    return {"status": "deleted"}

@router.patch("/{chat_id}")
async def rename_chat_session(
    chat_id: int,
    title: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Rename a chat session."""
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == chat_id, ChatSession.user_email == current_user["email"])
        .values(title=title)
    )
    await db.commit()
    return {"status": "renamed"}

@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Streaming chat endpoint."""
    chat_id = chat_request.chat_id
    query = chat_request.query
    logger.info(f"[CHAT_STREAM_START] User: {current_user['email']} | ChatID: {chat_id} | Query: {query[:50]}...")

    # 1. Get or Create Session
    if not chat_id:
        session = ChatSession(user_email=current_user["email"], title=query[:50])
        db.add(session)
        await db.commit()
        await db.refresh(session)
        chat_id = session.id
    else:
        # Verify ownership
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == chat_id, ChatSession.user_email == current_user["email"])
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

    # 2. Get History from DB
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_id)
        .order_by(desc(ChatMessage.timestamp))
        .limit(20) # Context window
    )
    db_messages = result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in reversed(db_messages)]

    # 3. Add User Message to DB
    user_msg = ChatMessage(session_id=chat_id, role="user", content=query)
    db.add(user_msg)
    
    # Update session title if it's the first message
    if not db_messages:
        session.title = query[:50]
    
    session.message_count += 1
    session.updated_at = datetime.now()
    await db.commit()

    # 4. Prepare Stream
    async def event_generator():
        # IMPORTANT: Use a fresh session inside the generator because the endpoint-level 'db' 
        # session will be closed as soon as we return the StreamingResponse.
        async with SessionLocal() as db_session:
            pipeline = RAGPipeline(db_session, current_user)
            full_response = ""
            
            # Send initial chat_id for frontend to track
            yield json.dumps({"chat_id": chat_id}) + "\n"

            try:
                async for chunk in pipeline.stream_query(query, history):
                    full_response += chunk
                    yield json.dumps({"token": chunk}) + "\n"
                
                # 5. Save Assistant Response to DB
                assistant_msg = ChatMessage(session_id=chat_id, role="assistant", content=full_response)
                db_session.add(assistant_msg)
                
                # Update session title/count
                await db_session.execute(
                    update(ChatSession)
                    .where(ChatSession.id == chat_id)
                    .values(message_count=ChatSession.message_count + 1, updated_at=datetime.now())
                )
                await db_session.commit()
                
                yield json.dumps({"status": "completed"}) + "\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

# Redundant imports removed
