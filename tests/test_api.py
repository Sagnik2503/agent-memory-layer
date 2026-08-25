import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.expensive
def test_chat_expense():
    response = client.post("/chat", json={"message": "I spent ₹500 on lunch"})
    assert response.status_code == 200
    assert "response" in response.json()

def test_chat_other():
    response = client.post("/chat", json={"message": "How are you?"})
    assert response.status_code == 200
    assert "response" in response.json()

@pytest.mark.expensive
def test_complete_expense_flow():
    response = client.post("/chat", json={"message": "I spent ₹500 on lunch"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "₹500" in data["response"]

def test_complete_other_flow():
    response = client.post("/chat", json={"message": "How are you?"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "track and understand your spending" in data["response"]