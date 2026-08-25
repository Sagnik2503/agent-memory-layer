import pytest
from app.graph.nodes import router_node, expense_extractor_node, validate_expense_node, response_node
from app.graph.state import AgentState
from app.models.expense import Expense, ValidationResult

def test_router_node_expense():
    state: AgentState = {
        "user_message": "I spent ₹500 on lunch",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    result = router_node(state)
    assert result["intent"] == "expense"

def test_router_node_other():
    state: AgentState = {
        "user_message": "How are you?",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    result = router_node(state)
    assert result["intent"] == "other"

@pytest.mark.expensive
def test_expense_extractor_node():
    state: AgentState = {
        "user_message": "I spent ₹500 on lunch",
        "intent": "expense",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    result = expense_extractor_node(state)
    assert "expense" in result
    assert result["expense"] is not None

def test_validate_expense_node_valid():
    expense = Expense(
        amount=500.0,
        currency="INR",
        category="food"
    )
    state: AgentState = {
        "user_message": "I spent ₹500 on lunch",
        "intent": "expense",
        "expense": expense,
        "validation_result": None,
        "response": ""
    }
    result = validate_expense_node(state)
    assert "validation_result" in result
    assert result["validation_result"].is_valid is True

def test_validate_expense_node_invalid():
    expense = Expense(
        amount=0.0,
        currency="INR",
        category="food"
    )
    state: AgentState = {
        "user_message": "I spent ₹500 on lunch",
        "intent": "expense",
        "expense": expense,
        "validation_result": None,
        "response": ""
    }
    result = validate_expense_node(state)
    assert result["validation_result"].is_valid is False

def test_response_node_other():
    state: AgentState = {
        "user_message": "How are you?",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    result = response_node(state)
    assert "response" in result
    assert "track and understand your spending" in result["response"]

def test_response_node_expense_valid():
    expense = Expense(
        amount=500.0,
        currency="INR",
        merchant="Swiggy",
        category="food",
        description="lunch"
    )
    validation_result = ValidationResult(
        is_valid=True,
        errors=[],
        missing_fields=[]
    )
    state: AgentState = {
        "user_message": "I spent ₹500 on lunch",
        "intent": "expense",
        "expense": expense,
        "validation_result": validation_result,
        "response": ""
    }
    result = response_node(state)
    assert "₹500" in result["response"]
    assert "Swiggy" in result["response"]

def test_router_node_error_handling():
    state: AgentState = {
        "user_message": "",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    result = router_node(state)
    assert result["intent"] == "other"

@pytest.mark.expensive
def test_expense_extractor_node_error():
    state: AgentState = {
        "user_message": "invalid message",
        "intent": "expense",
        "expense": None,
        "validation_result": None,
        "response": ""
    }
    result = expense_extractor_node(state)
    assert result["expense"] is None