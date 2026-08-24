import pytest
from app.graph.state import AgentState

def test_agent_state_creation():
    state: AgentState = {
        "user_message": "I spent ₹500 on lunch",
        "intent": "expense",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    assert state["user_message"] == "I spent ₹500 on lunch"
    assert state["intent"] == "expense"