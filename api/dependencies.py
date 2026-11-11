from application.services.case_service import CaseService
from infrastructure.langchain.vector_store import VectorStoreManager
from infrastructure.rag.rag_pipeline import ForensicRagPipeline

# Instantiate application singletons
case_service = CaseService()
vector_store_manager = VectorStoreManager()
rag_pipeline = ForensicRagPipeline(vector_store_manager)

def get_case_service() -> CaseService:
    return case_service

def get_rag_pipeline() -> ForensicRagPipeline:
    return rag_pipeline
