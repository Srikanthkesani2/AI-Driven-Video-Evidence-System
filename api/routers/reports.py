from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from api.dependencies import get_case_service
from application.services.case_service import CaseService
from utils.logger import logger

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/download/{case_id}")
def download_pdf_report(case_id: str, service: CaseService = Depends(get_case_service)):
    case_data = service.get_case(case_id)
    if not case_data:
        raise HTTPException(status_code=404, detail="Case not found.")
        
    report = case_data.get("report")
    if not report or not report.get("pdf_path"):
        raise HTTPException(
            status_code=400, 
            detail="Forensic report has not been generated for this case yet. Please complete video analysis first."
        )
        
    pdf_path = Path(report["pdf_path"])
    if not pdf_path.exists():
        logger.error(f"Report PDF file is missing from disk: {pdf_path}")
        raise HTTPException(status_code=500, detail="Forensic report PDF file is missing on server storage.")
        
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"Forensic_Report_{case_id}.pdf"
    )
