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
    save_expense_node,
    extract_query_node,
    execute_query_node,
    format_query_node,
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
    graph.add_node("save_expense", save_expense_node)
    graph.add_node("extract_query", extract_query_node)
    graph.add_node("execute_query", execute_query_node)
    graph.add_node("format_query", format_query_node)

    # Start
    graph.add_edge(START, "router")

    # Router
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "expense": "expense_extractor",
            "query": "extract_query",
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
    graph.add_edge("validate_expense", "save_expense")
    graph.add_edge("save_expense", "response")

    # Query flow
    graph.add_edge("extract_query", "execute_query")
    graph.add_edge("execute_query", "format_query")
    graph.add_edge("format_query", "response")

    # Response
    graph.add_edge("response", END)

    # Checkpointer
    checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)
