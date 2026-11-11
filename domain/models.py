from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class CaseStatus(str, Enum):
    DRAFT = "Draft"
    PENDING = "Pending"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"

class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class VideoMetadata(BaseModel):
    filename: str
    file_size: int
    duration_seconds: float
    resolution: str
    fps: float
    format: str
    thumbnail_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SpeechSegment(BaseModel):
    speaker: str
    text: str
    start_time: float  # seconds
    end_time: float    # seconds
    confidence: float

class OcrText(BaseModel):
    text: str
    timestamp: float   # seconds
    confidence: float
    bounding_box: Optional[List[float]] = None  # [x, y, w, h] normalized

class DetectedObject(BaseModel):
    label: str
    timestamp: float   # seconds
    confidence: float
    bounding_box: Optional[List[float]] = None  # [x, y, w, h] normalized

class DetectedPerson(BaseModel):
    person_id: str
    timestamp: float   # seconds
    confidence: float
    attributes: Dict[str, str] = Field(default_factory=dict)  # e.g. "clothing": "blue jacket", "backpack": "yes"
    bounding_box: Optional[List[float]] = None

class DetectedVehicle(BaseModel):
    vehicle_id: str
    timestamp: float   # seconds
    confidence: float
    license_plate: Optional[str] = None
    color: str
    type: str  # Sedan, SUV, Truck, etc.
    bounding_box: Optional[List[float]] = None

class TimelineEvent(BaseModel):
    timestamp: float   # seconds
    event_type: str    # e.g., "Person Entry", "Weapon Detection", "Object Exchange"
    description: str
    risk_level: RiskLevel
    confidence: float
    snapshot_path: Optional[str] = None

class RiskAnalysis(BaseModel):
    overall_score: int = Field(default=0, ge=0, le=100)
    risk_level: RiskLevel = RiskLevel.LOW
    factors: List[str] = Field(default_factory=list)
    confidence: float = 0.0

class ForensicReport(BaseModel):
    case_id: str
    executive_summary: str
    metadata: VideoMetadata
    timeline: List[TimelineEvent]
    transcript_summary: str
    risk_assessment: RiskAnalysis
    recommendations: List[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    pdf_path: Optional[str] = None

class EvidenceCase(BaseModel):
    case_id: str
    case_name: str
    description: Optional[str] = None
    officer_name: str
    status: CaseStatus = CaseStatus.PENDING
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    videos: List[str] = Field(default_factory=list)  # Video file names or IDs
    
    # Store dynamic aggregates
    objects_count: int = 0
    people_count: int = 0
    vehicles_count: int = 0
    weapons_count: int = 0
    processing_time_seconds: float = 0.0
