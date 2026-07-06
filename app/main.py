from fastapi import FastAPI, Depends, HTTPException # Reload Trigger - SYNC 1
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import time
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.vehicles import router as vehicles_router
from app.api.telemetry import router as telemetry_router
from app.api.embeddings import router as embeddings_router
from app.api.stats import router as stats_router
from app.api.traccar_webhooks import router as traccar_webhooks_router
from app.api.analytics import router as analytics_router
# from app.api.sync import router as sync_router  # DISABLED: sync services stopped
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

# Static Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "static"))

# Mount static files for assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Debug Routes
@app.get("/api/debug/routes")
async def list_routes():
    return [{"path": route.path, "name": route.name} for route in app.routes if hasattr(route, 'path')]

from app.api.settings import router as settings_router
from app.api.data_import import router as data_import_router
# Include Routers
app.include_router(data_import_router, prefix="/api/fleet/fdb", tags=["FDB"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(vehicles_router, prefix="/api/v1/vehicles", tags=["Vehicles"])
app.include_router(telemetry_router, prefix="/api/v1/telemetry", tags=["Telemetry"])
app.include_router(embeddings_router, prefix="/api/v1/embeddings", tags=["Embeddings"])
app.include_router(stats_router, prefix="/api/v1/stats", tags=["Stats"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
# app.include_router(sync_router, prefix="/api/v1/sync", tags=["Sync"])  # DISABLED: sync services stopped
app.include_router(traccar_webhooks_router, prefix="/api/traccar/webhook", tags=["Webhooks"])
app.include_router(proxy_router, prefix="/api/traccar", tags=["Traccar Proxy"])
app.include_router(settings_router, prefix="/api/v1/settings", tags=["Settings"])

@app.get("/")
async def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
    return {"message": "AI - Telemetrix Backend Active. Static UI missing."}

# Catch-all for static assets and client-side routing
@app.get("/{rest_of_path:path}")
async def serve_static(rest_of_path: str = ""):
    file_path = os.path.join(STATIC_DIR, rest_of_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})
    return FileResponse(os.path.join(STATIC_DIR, "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
