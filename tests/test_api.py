from fastapi.testclient import TestClient
from api.main import app
from domain.models import CaseStatus

client = TestClient(app)

def test_api_list_cases():
    response = client.get("/api/cases")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_api_create_case():
    payload = {
        "case_name": "Jewelry Store Alarm Trigger",
        "officer_name": "Agent Cooper",
        "description": "Perimeter camera motion logs"
    }
    response = client.post("/api/cases", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["case_name"] == "Jewelry Store Alarm Trigger"
    assert data["officer_name"] == "Agent Cooper"
    assert data["status"] == "Pending"

def test_api_dashboard_stats():
    response = client.get("/api/cases/stats")
    assert response.status_code == 200
    data = response.json()
    assert "cards" in data
    assert "charts" in data
    assert "recent" in data
    assert "videos_processed" in data["cards"]
    assert "active_investigations" in data["cards"]

def test_api_chat_assistant():
    # Create a temporary case to ask questions about
    payload = {
        "case_name": "Chat Test Case",
        "officer_name": "Agent Cooper"
    }
    c_res = client.post("/api/cases", json=payload).json()
    case_id = c_res["case_id"]

    chat_payload = {
        "case_id": case_id,
        "query": "Who carried a backpack?"
    }
    response = client.post("/api/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "answer" in data
    assert "retrieved_evidence" in data
