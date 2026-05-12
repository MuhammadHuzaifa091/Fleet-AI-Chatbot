from fastapi import FastAPI, Depends, HTTPException # Reload Trigger
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.vehicles import router as vehicles_router
from app.api.telemetry import router as telemetry_router
from app.api.embeddings import router as embeddings_router
from app.api.stats import router as stats_router
from app.api.analytics import router as analytics_router
from app.api.proxy import router as proxy_router
from app.core.config import settings
from app.core.limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from loguru import logger
import sys
import os

# Configure Loguru
logger.remove()
logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>", level=settings.LOG_LEVEL)
logger.add("logs/app.log", rotation="10 MB", retention="10 days", level="DEBUG")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade AI-powered Fleet Intelligence RAG Platform",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, "index.html"))

# Debug Routes
@app.get("/api/debug/routes")
async def list_routes():
    return [{"path": route.path, "name": route.name} for route in app.routes if hasattr(route, 'path')]

# Include Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(vehicles_router, prefix="/api/v1/vehicles", tags=["Vehicles"])
app.include_router(telemetry_router, prefix="/api/v1/telemetry", tags=["Telemetry"])
app.include_router(embeddings_router, prefix="/api/v1/embeddings", tags=["Embeddings"])
app.include_router(stats_router, prefix="/api/v1/stats", tags=["Stats"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(proxy_router, prefix="/api/traccar", tags=["Traccar Proxy"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
