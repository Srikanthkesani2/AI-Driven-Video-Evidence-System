import pytest
from pathlib import Path
from application.services.case_service import CaseService
from domain.models import CaseStatus, RiskLevel

def test_case_creation():
    service = CaseService()
    case = service.create_case(
        case_name="Security Vault Intrusion",
        officer_name="Officer Jones",
        description="Foyer sensor logs triggered at 22:00"
    )
    
    assert case.case_id is not None
    assert case.case_name == "Security Vault Intrusion"
    assert case.officer_name == "Officer Jones"
    assert case.status == CaseStatus.PENDING

def test_add_video_to_case():
    service = CaseService()
    case = service.create_case("Theft Scan", "Officer Jones")
    
    # Add video
    success = service.add_video_to_case(case.case_id, "theft_foyer.mp4")
    assert success is True
    
    # Verify addition
    c_updated = service.get_case(case.case_id)
    assert "theft_foyer.mp4" in c_updated["videos"]

def test_update_case_fields():
    service = CaseService()
    case = service.create_case("Hazard Scan", "Officer Jones")
    
    service.update_case_fields(case.case_id, {
        "risk_level": RiskLevel.HIGH.value,
        "risk_score": 75,
        "status": CaseStatus.COMPLETED.value
    })
    
    c_updated = service.get_case(case.case_id)
    assert c_updated["risk_level"] == "High"
    assert c_updated["risk_score"] == 75
    assert c_updated["status"] == "Completed"
