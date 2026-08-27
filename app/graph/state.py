from typing import TypedDict, Optional, Literal, Annotated
from app.models.expense import Expense, ValidationResult
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    user_message: str
    intent: Literal["expense", "other", "needs_clarification"]
    expense: Optional[Expense]
    validation_result: Optional[ValidationResult]
    response: str
    clarification_history: list[dict]
    clarification_rounds: int
