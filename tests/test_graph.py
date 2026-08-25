import pytest
from app.graph.graph import create_expense_graph

def test_create_expense_graph():
    graph = create_expense_graph()
    assert graph is not None
    result = graph.invoke({
        "user_message": "How are you?",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    })
    assert "response" in result

def test_other_flow():
    graph = create_expense_graph()
    result = graph.invoke({
        "user_message": "How are you?",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    })
    assert result["intent"] == "other"
    assert "track and understand your spending" in result["response"]

@pytest.mark.expensive
def test_expense_flow():
    graph = create_expense_graph()
    result = graph.invoke({
        "user_message": "I spent ₹500 on lunch",
        "intent": "other",
        "expense": None,
        "validation_result": None,
        "response": ""
    })
    assert result["intent"] == "expense"
    assert result["expense"] is not None
    assert result["validation_result"] is not None
    assert "₹500" in result["response"]