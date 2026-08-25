from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import (
    router_node,
    expense_extractor_node,
    validate_expense_node,
    response_node
)

def create_expense_graph():
    """Create the expense tracker LangGraph"""
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("expense_extractor", expense_extractor_node)
    graph.add_node("validate_expense", validate_expense_node)
    graph.add_node("response", response_node)
    
    # Set entry point
    graph.set_entry_point("router")
    
    # Add conditional edges from router
    graph.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {
            "expense": "expense_extractor",
            "other": "response"
        }
    )
    
    # Add linear edges for expense path
    graph.add_edge("expense_extractor", "validate_expense")
    graph.add_edge("validate_expense", "response")
    
    # Add edge from response to END
    graph.add_edge("response", END)
    
    return graph.compile()