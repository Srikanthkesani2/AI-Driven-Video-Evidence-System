import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from domain.models import EvidenceCase, CaseStatus, RiskLevel
from infrastructure.langgraph.workflow import compiled_workflow
from utils.logger import logger
from config.config import settings

class CaseService:
    def __init__(self):
        self.db_path = settings.app.output_path / "cases.json"
        self._initialize_db()

    def _initialize_db(self):
        if not self.db_path.exists():
            with open(self.db_path, "w") as f:
                json.dump({}, f)

    def _read_db(self) -> Dict[str, Any]:
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_db(self, data: Dict[str, Any]):
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def create_case(self, case_name: str, officer_name: str, description: Optional[str] = None) -> EvidenceCase:
        db = self._read_db()
        case_id = f"CASE-{int(time.time())}"
        
        new_case = EvidenceCase(
            case_id=case_id,
            case_name=case_name,
            officer_name=officer_name,
            description=description,
            status=CaseStatus.PENDING,
            risk_level=RiskLevel.LOW,
            risk_score=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db[case_id] = new_case.model_dump()
        self._write_db(db)
        logger.info(f"Created new Case record: {case_id} ('{case_name}')")
        return new_case

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        db = self._read_db()
        return db.get(case_id)

    def list_cases(self) -> List[Dict[str, Any]]:
        db = self._read_db()
        # Return sorted by created_at descending
        cases = list(db.values())
        cases.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return cases

    def add_video_to_case(self, case_id: str, filename: str) -> bool:
        db = self._read_db()
        if case_id not in db:
            return False
            
        case_data = db[case_id]
        if filename not in case_data["videos"]:
            case_data["videos"].append(filename)
            case_data["updated_at"] = str(datetime.utcnow())
            self._write_db(db)
            return True
        return False

    def update_case_fields(self, case_id: str, updates: Dict[str, Any]):
        db = self._read_db()
        if case_id not in db:
            return
            
        case_data = db[case_id]
        for key, value in updates.items():
            case_data[key] = value
            
        case_data["updated_at"] = str(datetime.utcnow())
        self._write_db(db)

    async def run_pipeline_async(self, case_id: str, video_filename: str):
        """Asynchronous worker that fires the LangGraph pipeline and updates status."""
        logger.info(f"Starting async processing thread for Case: {case_id}, Video: {video_filename}")
        
        db = self._read_db()
        case_data = db.get(case_id)
        if not case_data:
            logger.error(f"Cannot run pipeline, case {case_id} does not exist.")
            return

        self.update_case_fields(case_id, {
            "status": CaseStatus.PROCESSING.value,
            "current_stage": "Upload"
        })

        video_path = settings.app.upload_path / video_filename
        
        # Build initial LangGraph workflow state
        inputs = {
            "case_id": case_id,
            "case_name": case_data["case_name"],
            "officer_name": case_data["officer_name"],
            "video_path": str(video_path),
            "video_metadata": {},
            "speech_transcript": [],
            "ocr_text": [],
            "detected_objects": [],
            "detected_persons": [],
            "detected_vehicles": [],
            "etl_results": {},
            "embeddings_status": "PENDING",
            "evidence_verified": False,
            "risk_score": 0,
            "risk_level": "Low",
            "timeline": [],
            "report": {},
            "current_stage": "Upload",
            "retry_count": 0,
            "errors": []
        }

        # Run compilation
        try:
            # We wrap the invocation to inspect progress or run in executor
            # Since our nodes have small sleeps, we run compiled_workflow.invoke
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(None, lambda: compiled_workflow.invoke(inputs))
            
            if final_state.get("errors"):
                logger.error(f"LangGraph execution ended with errors: {final_state['errors']}")
                self.update_case_fields(case_id, {
                    "status": CaseStatus.FAILED.value,
                    "errors": final_state["errors"],
                    "current_stage": "FAILED"
                })
            else:
                logger.info(f"LangGraph execution completed successfully for case {case_id}")
                
                # Fetch aggregates from ETL
                etl = final_state.get("etl_results", {})
                aggs = etl.get("aggregates", {})
                
                self.update_case_fields(case_id, {
                    "status": CaseStatus.COMPLETED.value,
                    "risk_level": final_state.get("risk_level"),
                    "risk_score": final_state.get("risk_score"),
                    "objects_count": aggs.get("objects_count", 0),
                    "people_count": aggs.get("people_count", 0),
                    "vehicles_count": aggs.get("vehicles_count", 0),
                    "weapons_count": aggs.get("weapons_count", 0),
                    "processing_time_seconds": etl.get("processing_time_seconds", 0.0),
                    "current_stage": "Completed",
                    "timeline": final_state.get("timeline", []),
                    "speech_transcript": final_state.get("speech_transcript", []),
                    "ocr_text": final_state.get("ocr_text", []),
                    "report": final_state.get("report", {})
                })
        except Exception as e:
            logger.exception(f"Unexpected crash in LangGraph processing node: {e}")
            self.update_case_fields(case_id, {
                "status": CaseStatus.FAILED.value,
                "current_stage": "FAILED",
                "errors": [str(e)]
            })
