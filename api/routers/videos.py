import asyncio
from pathlib import Path
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from api.dependencies import get_case_service
from application.services.case_service import CaseService
from utils.video_helper import generate_video_thumbnail
from config.config import settings
from utils.logger import logger

router = APIRouter(prefix="/videos", tags=["Videos"])

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

@router.post("/upload")
async def upload_video(
    case_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: CaseService = Depends(get_case_service)
):
    case_data = service.get_case(case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '{suffix}'. Allowed formats: MP4, AVI, MOV, MKV"
        )

    # Clean filename and build paths
    safe_filename = f"{case_id}_{int(asyncio.get_event_loop().time())}{suffix}"
    upload_path = settings.app.upload_path / safe_filename
    
    logger.info(f"Saving uploaded file {file.filename} to {upload_path}")
    
    # Save file contents chunk by chunk
    try:
        with open(upload_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                buffer.write(content)
    except Exception as e:
        logger.error(f"Failed to write uploaded file to disk: {e}")
        raise HTTPException(status_code=500, detail="Failed to save video to file system.")

    # Generate video thumbnail preview
    processed_dir = settings.app.output_path / "thumbnails"
    thumbnail_url = generate_video_thumbnail(upload_path, processed_dir)
    
    # Link video metadata details in Case Database
    service.add_video_to_case(case_id, safe_filename)
    service.update_case_fields(case_id, {
        "thumbnail_url": thumbnail_url,
        "video_filename": safe_filename
    })

    # Trigger the stateful LangGraph pipeline in the background
    background_tasks.add_task(service.run_pipeline_async, case_id, safe_filename)

    return {
        "status": "UPLOADED",
        "filename": safe_filename,
        "thumbnail_url": thumbnail_url,
        "message": "Video uploaded successfully. AI processing pipeline triggered in background."
    }
