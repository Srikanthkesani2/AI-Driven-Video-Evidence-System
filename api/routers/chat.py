from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.dependencies import get_rag_pipeline
from infrastructure.rag.rag_pipeline import ForensicRagPipeline

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatQueryRequest(BaseModel):
    case_id: str
    query: str

@router.post("")
def ask_assistant(req: ChatQueryRequest, rag: ForensicRagPipeline = Depends(get_rag_pipeline)):
    if not req.case_id or not req.query:
        raise HTTPException(status_code=400, detail="case_id and query are required parameters.")
    
    try:
        response = rag.answer_question(req.case_id, req.query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process chat query: {str(e)}")
