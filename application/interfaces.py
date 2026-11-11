from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any
from domain.models import (
    VideoMetadata, SpeechSegment, OcrText, DetectedObject,
    DetectedPerson, DetectedVehicle, ForensicReport, RiskAnalysis, TimelineEvent
)

class IAzureAIClient(ABC):
    @abstractmethod
    def extract_metadata(self, video_path: Path) -> VideoMetadata:
        """Extract basic video details (fps, duration, format)."""
        pass

    @abstractmethod
    def analyze_speech(self, video_path: Path) -> List[SpeechSegment]:
        """Perform Speech-to-Text and return time-stamped text segments."""
        pass

    @abstractmethod
    def analyze_ocr(self, video_path: Path) -> List[OcrText]:
        """Perform optical character recognition across video frames."""
        pass

    @abstractmethod
    def analyze_vision(self, video_path: Path) -> Dict[str, List[Any]]:
        """Run object, face, and weapon detection. Returns lists of objects, persons, vehicles."""
        pass


class IDatabricksClient(ABC):
    @abstractmethod
    def trigger_etl_job(self, case_id: str, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a spark ETL job to clean, normalize, validate, and aggregate metadata."""
        pass


class IVectorStoreManager(ABC):
    @abstractmethod
    def index_evidence(self, case_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Embed and write structured text blocks into the search database."""
        pass

    @abstractmethod
    def retrieve_evidence(self, case_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a given natural language query."""
        pass


class IPdfGenerator(ABC):
    @abstractmethod
    def generate_forensic_pdf(self, report: ForensicReport) -> Path:
        """Render a formatted, ready-to-print Forensic Report to disk."""
        pass
