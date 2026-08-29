from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.graph.nodes import (
    router_node,
    expense_extractor_node,
    validate_expense_node,
    clarification_node,
    merge_clarification_node,
    response_node,
)


def route_after_router(state: AgentState):
    return state["intent"]


def route_after_validation(state: AgentState):
    validation = state["validation_result"]

    if validation.is_valid:
        return "response"

    if validation.missing_fields:
        return "clarification"

    return "response"


def create_expense_graph():
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("router", router_node)
    graph.add_node("expense_extractor", expense_extractor_node)
    graph.add_node("validate_expense", validate_expense_node)
    graph.add_node("clarification", clarification_node)
    graph.add_node("merge_clarification", merge_clarification_node)
    graph.add_node("response", response_node)

    # Start
    graph.add_edge(START, "router")

    # Router
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "expense": "expense_extractor",
            "other": "response",
        },
    )

    # Expense extraction
    graph.add_edge(
        "expense_extractor",
        "validate_expense",
    )

    # Validation
    graph.add_conditional_edges(
        "validate_expense",
        route_after_validation,
        {
            "clarification": "clarification",
            "response": "response",
        },
    )

    # Clarification
    graph.add_edge(
        "clarification",
        "merge_clarification",
    )

    # Re-validate after clarification
    graph.add_edge(
        "merge_clarification",
        "validate_expense",
    )

    # Response
    graph.add_edge("response", END)

    # Checkpointer
    checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
