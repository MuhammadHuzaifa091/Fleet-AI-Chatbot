from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
from app.api.auth import get_current_user
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.traccar import User
from app.core.config import settings
from typing import Dict, Any

router = APIRouter()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_traccar(
    path: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Fetch JSESSIONID for the current user
    # Note: current_user only has id, email, role, name. We need the attributes.
    query = select(User).where(User.email == current_user["email"])
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not user.attributes or "jsessionid" not in user.attributes:
         raise HTTPException(status_code=401, detail="No active Traccar session found. Please re-login.")
    
    jsessionid = user.attributes["jsessionid"]
    
    # 2. Prepare Proxy Request
    url = f"{settings.TRACCAR_URL}/api/{path}"
    if request.query_params:
        url += f"?{request.query_params}"
        
    headers = dict(request.headers)
    # Remove local host headers to prevent confusion
    headers.pop("host", None)
    headers.pop("authorization", None) # Use session cookie instead
    
    # Inject Traccar Session Cookie
    cookies = {"JSESSIONID": jsessionid}
    
    async with httpx.AsyncClient() as client:
        try:
            content = await request.body()
            proxy_resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=content,
                cookies=cookies,
                timeout=10.0
            )
            
            # 3. Return Traccar Response
            return Response(
                content=proxy_resp.content,
                status_code=proxy_resp.status_code,
                headers=dict(proxy_resp.headers)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")
