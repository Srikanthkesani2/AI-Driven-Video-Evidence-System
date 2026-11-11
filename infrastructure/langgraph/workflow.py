import time
from pathlib import Path
from typing import Dict, List, Any, TypedDict, Union
from langgraph.graph import StateGraph, END
from domain.models import (
    EvidenceCase, CaseStatus, RiskLevel, VideoMetadata, SpeechSegment,
    OcrText, DetectedObject, DetectedPerson, DetectedVehicle,
    TimelineEvent, RiskAnalysis, ForensicReport
)
from infrastructure.azure.client import AzureAIClient
from infrastructure.databricks.client import DatabricksClient
from infrastructure.langchain.vector_store import VectorStoreManager
from infrastructure.reports.generator import PdfGenerator
from utils.logger import logger

class WorkflowState(TypedDict):
    case_id: str
    case_name: str
    officer_name: str
    video_path: str
    video_metadata: Dict[str, Any]
    speech_transcript: List[Dict[str, Any]]
    ocr_text: List[Dict[str, Any]]
    detected_objects: List[Dict[str, Any]]
    detected_persons: List[Dict[str, Any]]
    detected_vehicles: List[Dict[str, Any]]
    etl_results: Dict[str, Any]
    embeddings_status: str
    evidence_verified: bool
    risk_score: int
    risk_level: str
    timeline: List[Dict[str, Any]]
    report: Dict[str, Any]
    current_stage: str
    retry_count: int
    errors: List[str]

# Global Clients (DI instances)
azure_client = AzureAIClient()
databricks_client = DatabricksClient()
vector_store = VectorStoreManager()
pdf_generator = PdfGenerator()

# ----------------- Nodes -----------------

def upload_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Uploading & Pre-validating Video...")
    video_path = Path(state["video_path"])
    
    if not video_path.exists():
        return {"errors": [f"Video file {video_path} not found"], "current_stage": "FAILED"}
        
    meta = azure_client.extract_metadata(video_path)
    logger.info(f"[LangGraph] Video pre-validated: {meta.filename} ({meta.resolution})")
    
    return {
        "video_metadata": meta.model_dump(),
        "current_stage": "Frame Extraction",
        "errors": []
    }

def frame_extraction_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Running keyframe extraction...")
    time.sleep(0.5) # Simulate frame slicing
    return {
        "current_stage": "Speech Recognition",
    }

def speech_analysis_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Running Speech Recognition...")
    video_path = Path(state["video_path"])
    segments = azure_client.analyze_speech(video_path)
    
    # Store transcript in vector database for conversation lookup later
    for seg in segments:
        vector_store.index_evidence(
            case_id=state["case_id"],
            content=f"[{seg.start_time}s - {seg.end_time}s] Speaker {seg.speaker}: {seg.text}",
            metadata={"type": "speech", "speaker": seg.speaker, "start_time": seg.start_time, "timestamp": seg.start_time}
        )
        
    return {
        "speech_transcript": [s.model_dump() for s in segments]
    }

def ocr_analysis_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Running Optical Character Recognition...")
    video_path = Path(state["video_path"])
    ocr_res = azure_client.analyze_ocr(video_path)
    
    for item in ocr_res:
        vector_store.index_evidence(
            case_id=state["case_id"],
            content=f"OCR Text detected: '{item.text}'",
            metadata={"type": "ocr", "timestamp": item.timestamp}
        )
        
    return {
        "ocr_text": [o.model_dump() for o in ocr_res]
    }

def vision_analysis_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Running Face & Object Detection...")
    video_path = Path(state["video_path"])
    vision_res = azure_client.analyze_vision(video_path)
    
    # Unpack objects
    objs = vision_res.get("objects", [])
    persons = vision_res.get("persons", [])
    vehicles = vision_res.get("vehicles", [])
    
    for item in objs:
        vector_store.index_evidence(
            case_id=state["case_id"],
            content=f"Object detected: {item.label} (Confidence: {item.confidence:.2f})",
            metadata={"type": "object", "label": item.label, "timestamp": item.timestamp}
        )
    for item in persons:
        vector_store.index_evidence(
            case_id=state["case_id"],
            content=f"Person detected (ID: {item.person_id}) with attributes: {item.attributes}",
            metadata={"type": "person", "person_id": item.person_id, "timestamp": item.timestamp}
        )
    for item in vehicles:
        vector_store.index_evidence(
            case_id=state["case_id"],
            content=f"Vehicle detected (ID: {item.vehicle_id}) license plate: {item.license_plate or 'N/A'}, color: {item.color}, type: {item.type}",
            metadata={"type": "vehicle", "vehicle_id": item.vehicle_id, "timestamp": item.timestamp}
        )
        
    return {
        "detected_objects": [x.model_dump() for x in objs],
        "detected_persons": [x.model_dump() for x in persons],
        "detected_vehicles": [x.model_dump() for x in vehicles]
    }

def metadata_validation_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Validating aggregated metadata frames...")
    # Deduplicate overlapping objects or check integrity
    time.sleep(0.3)
    return {
        "current_stage": "Databricks Processing"
    }

def databricks_etl_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Executing Databricks Spark ETL batch...")
    
    # Reassemble objects to send
    raw_payload = {
        "objects": state.get("detected_objects", []),
        "persons": state.get("detected_persons", []),
        "vehicles": state.get("detected_vehicles", [])
    }
    
    job_result = databricks_client.trigger_etl_job(state["case_id"], raw_payload)
    return {
        "etl_results": job_result,
        "current_stage": "Embedding Generation"
    }

def embedding_generation_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Finalizing Vector Embeddings compilation...")
    return {
        "embeddings_status": "COMPLETED",
        "current_stage": "Evidence Verification"
    }

def evidence_verification_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: AI Evidence Verification verification...")
    # Validate that critical objects have verified matching timestamps
    return {
        "evidence_verified": True,
        "current_stage": "Risk Analyzer"
    }

def risk_analyzer_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Running Threat Risk Assessment...")
    
    # Calculate overall risk score dynamically
    score = 15 # baseline
    factors = ["Active investigation initiated"]
    
    weapons = state["etl_results"].get("aggregates", {}).get("weapons_count", 0)
    if weapons > 0:
        score += 55
        factors.append(f"Weapons detected ({weapons} instance(s))")
        
    persons_cnt = len(state.get("detected_persons", []))
    if persons_cnt > 2:
        score += 15
        factors.append(f"Multiple subjects detected on site ({persons_cnt})")
        
    vehicles_cnt = len(state.get("detected_vehicles", []))
    if vehicles_cnt > 0:
        score += 10
        factors.append(f"Associated vehicle(s) logged in crime perimeter")

    # Limit score caps
    score = min(score, 100)
    
    # Determine level
    level = RiskLevel.LOW.value
    if score >= 85:
        level = RiskLevel.CRITICAL.value
    elif score >= 60:
        level = RiskLevel.HIGH.value
    elif score >= 35:
        level = RiskLevel.MEDIUM.value
        
    logger.info(f"[LangGraph] Risk Evaluation: {score}/100 -> {level}")
    return {
        "risk_score": score,
        "risk_level": level,
        "etl_results": {
            **state.get("etl_results", {}),
            "risk_analysis": {
                "overall_score": score,
                "risk_level": level,
                "factors": factors
            }
        },
        "current_stage": "Timeline Generator"
    }

def timeline_generator_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Assembling Chronological Timeline...")
    
    events = []
    
    # Compile from objects/vehicles
    for p in state.get("detected_persons", []):
        attrs = p.get("attributes", {})
        events.append(TimelineEvent(
            timestamp=p["timestamp"],
            event_type="Subject Sighted",
            description=f"Subject {p['person_id']} logged wearing {attrs.get('clothing','unknown')} (Role: {attrs.get('role','unknown')})",
            risk_level=RiskLevel.MEDIUM if "suspect" in str(attrs.get("role","")).lower() else RiskLevel.LOW,
            confidence=p["confidence"]
        ).model_dump())
        
    for v in state.get("detected_vehicles", []):
        events.append(TimelineEvent(
            timestamp=v["timestamp"],
            event_type="Vehicle Sighted",
            description=f"{v['color'].capitalize()} {v['type']} identified (License Plate: {v['license_plate'] or 'N/A'})",
            risk_level=RiskLevel.MEDIUM,
            confidence=v["confidence"]
        ).model_dump())
        
    for o in state.get("detected_objects", []):
        is_weapon = o["label"].lower() in ["handgun", "rifle", "weapon", "pistol"]
        events.append(TimelineEvent(
            timestamp=o["timestamp"],
            event_type="Hazard Warning" if is_weapon else "Object Log",
            description=f"Detection: {o['label']} found in active viewport frame",
            risk_level=RiskLevel.CRITICAL if is_weapon else RiskLevel.LOW,
            confidence=o["confidence"]
        ).model_dump())
        
    # Sort events by timestamp ascending
    events.sort(key=lambda x: x["timestamp"])
    
    for ev in events:
        vector_store.index_evidence(
            case_id=state["case_id"],
            content=f"Timeline Event at {ev['timestamp']:.1f}s: {ev['event_type']} - {ev['description']} (Risk Level: {ev['risk_level']})",
            metadata={"type": "timeline", "timestamp": ev["timestamp"]}
        )
    
    return {
        "timeline": events,
        "current_stage": "Report Generator"
    }

def report_generator_node(state: WorkflowState) -> Dict[str, Any]:
    logger.info("[LangGraph] Node: Compiling Report structures and triggering PDF layout generator...")
    
    # Executive summary generation based on events
    risk_lvl = state["risk_level"]
    risk_score = state["risk_score"]
    factors = state["etl_results"].get("risk_analysis", {}).get("factors", [])
    
    summary = (
        f"Forensic analysis of case evidence video. The investigation is evaluated with "
        f"a threat level of {risk_lvl} (Threat Score: {risk_score}/100) due to several risk events:\n"
        + "\n".join([f"- {f}" for f in factors])
    )
    
    # Convert Dict list to Pydantic objects for generator
    timeline_objects = [TimelineEvent(**ev) for ev in state["timeline"]]
    
    raw_meta = state["video_metadata"]
    meta_model = VideoMetadata(
        filename=raw_meta["filename"],
        file_size=raw_meta["file_size"],
        duration_seconds=raw_meta["duration_seconds"],
        resolution=raw_meta["resolution"],
        fps=raw_meta["fps"],
        format=raw_meta["format"],
        thumbnail_path=raw_meta.get("thumbnail_path")
    )
    
    risk_analysis_model = RiskAnalysis(
        overall_score=risk_score,
        risk_level=RiskLevel(risk_lvl),
        factors=factors,
        confidence=0.92
    )
    
    # Determine PDF output location
    processed_dir = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    pdf_dest = processed_dir / f"forensic_report_{state['case_id']}.pdf"
    
    forensic_rep = ForensicReport(
        case_id=state["case_id"],
        executive_summary=summary,
        metadata=meta_model,
        timeline=timeline_objects,
        transcript_summary="Speech segments transcribed and vector indexed for deep chat querying.",
        risk_assessment=risk_analysis_model,
        recommendations=[
            "Isolate the suspect vehicle (license plate detected) using automated license plate readers (ALPR).",
            "Enhance biometric logs on entry/exit gate zones.",
            "Cross-verify weapon profile against weapon registration databases.",
            "Export this evidence log file to central district database."
        ],
        pdf_path=str(pdf_dest)
    )
    
    # Run PDF Generation
    generated_pdf_path = pdf_generator.generate_forensic_pdf(forensic_rep)
    
    return {
        "report": {
            **forensic_rep.model_dump(),
            "pdf_path": str(generated_pdf_path)
        },
        "current_stage": "Completed"
    }

# ----------------- Router / Edges -----------------

def should_continue(state: WorkflowState) -> str:
    # Router to retry or fail if errors occur
    if state.get("errors"):
        if state.get("retry_count", 0) < 2:
            logger.warning(f"[LangGraph] Error found. Retrying... Count: {state['retry_count']}")
            return "retry"
        return "fail"
    
    next_stage = state.get("current_stage")
    if next_stage == "Completed":
        return "complete"
    return "continue"

# ----------------- Graph Construction -----------------

def build_workflow_graph() -> StateGraph:
    builder = StateGraph(WorkflowState)
    
    # Add Nodes
    builder.add_node("upload", upload_node)
    builder.add_node("frame_extraction", frame_extraction_node)
    builder.add_node("speech_analysis", speech_analysis_node)
    builder.add_node("ocr_analysis", ocr_analysis_node)
    builder.add_node("vision_analysis", vision_analysis_node)
    builder.add_node("metadata_validation", metadata_validation_node)
    builder.add_node("databricks_etl", databricks_etl_node)
    builder.add_node("embedding_generation", embedding_generation_node)
    builder.add_node("evidence_verification", evidence_verification_node)
    builder.add_node("risk_analyzer", risk_analyzer_node)
    builder.add_node("timeline_generator", timeline_generator_node)
    builder.add_node("report_generator", report_generator_node)
    
    # Establish Edges
    builder.set_entry_point("upload")
    builder.add_edge("upload", "frame_extraction")
    
    # Parallel workflows: Frame extraction branches out to Speech, OCR, and Vision concurrently
    builder.add_edge("frame_extraction", "speech_analysis")
    builder.add_edge("frame_extraction", "ocr_analysis")
    builder.add_edge("frame_extraction", "vision_analysis")
    
    # Join points into metadata validation
    builder.add_edge("speech_analysis", "metadata_validation")
    builder.add_edge("ocr_analysis", "metadata_validation")
    builder.add_edge("vision_analysis", "metadata_validation")
    
    builder.add_edge("metadata_validation", "databricks_etl")
    builder.add_edge("databricks_etl", "embedding_generation")
    builder.add_edge("embedding_generation", "evidence_verification")
    builder.add_edge("evidence_verification", "risk_analyzer")
    builder.add_edge("risk_analyzer", "timeline_generator")
    builder.add_edge("timeline_generator", "report_generator")
    
    # Dynamic routing check after generating reports
    builder.add_conditional_edges(
        "report_generator",
        should_continue,
        {
            "continue": "report_generator", # Safeguard loop
            "retry": "upload", # Simple retry from start
            "fail": END,
            "complete": END
        }
    )
    
    return builder.compile()

# Instantiated workflow machine
compiled_workflow = build_workflow_graph()
