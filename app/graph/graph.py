from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes import (
    router_node,
    clarification_node,
    expense_extractor_node,
    validate_expense_node,
    response_node,
)


def create_expense_graph():
    """Create the expense tracker LangGraph"""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("expense_extractor", expense_extractor_node)
    graph.add_node("validate_expense", validate_expense_node)
    graph.add_node("response", response_node)

    # Set entry point
    graph.set_entry_point("router")

    # Router routes based on intent
    graph.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {
            "expense": "clarification",
            "other": "response",
        },
    )

    # Clarification routes based on clarity check
    graph.add_conditional_edges(
        "clarification",
        lambda state: state["intent"],
        {
            "expense": "expense_extractor",
            "needs_clarification": "response",
        },
    )

    # Expense path: extract -> validate -> respond
    graph.add_edge("expense_extractor", "validate_expense")
    graph.add_edge("validate_expense", "response")

    # All paths end at END after response
    graph.add_edge("response", END)

    return graph.compile()
