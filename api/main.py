import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routers import cases, videos, chat, reports
from config.config import settings
from utils.logger import logger

app = FastAPI(
    title="AI-Driven Video Evidence Analysis System - Enterprise Edition",
    description="Backend API services for forensic video analytics and investigation pipelines",
    version="1.0.0"
)

# CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup directories creation
@app.on_event("startup")
def bootstrap_directories():
    logger.info("Bootstrapping storage directories...")
    settings.app.upload_path.mkdir(parents=True, exist_ok=True)
    settings.app.output_path.mkdir(parents=True, exist_ok=True)
    (settings.app.output_path / "thumbnails").mkdir(parents=True, exist_ok=True)
    (settings.app.output_path / "thumbnails" / "assets").mkdir(parents=True, exist_ok=True)
    
    # Create static subdirs
    static_path = Path(__file__).resolve().parent.parent / "static"
    (static_path / "css").mkdir(parents=True, exist_ok=True)
    (static_path / "js").mkdir(parents=True, exist_ok=True)
    (static_path / "assets").mkdir(parents=True, exist_ok=True)

# Register routers
app.include_router(cases.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

# Ensure directories exist before mounting static paths
data_dir = Path(__file__).resolve().parent.parent / "data"
(data_dir / "uploads").mkdir(parents=True, exist_ok=True)
(data_dir / "processed").mkdir(parents=True, exist_ok=True)
(data_dir / "processed" / "thumbnails").mkdir(parents=True, exist_ok=True)

# Mount dynamic uploads and output folders inside static paths for streaming & preview
app.mount("/static/uploads", StaticFiles(directory=str(data_dir / "uploads")), name="uploads")
app.mount("/static/processed", StaticFiles(directory=str(data_dir / "processed")), name="processed")

# Serve SPA static files
static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def serve_home():
    return FileResponse(static_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    logger.info("Launching FastAPI server...")
    uvicorn.run("api.main:app", host=settings.app.host, port=settings.app.port, reload=settings.app.debug)
