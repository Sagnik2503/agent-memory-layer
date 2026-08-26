from typing import TypedDict, Optional, Literal
from app.models.expense import Expense, ValidationResult


class AgentState(TypedDict):
    user_message: str
    intent: Literal["expense", "other"]
    expense: list[Expense] = []
    validation_result: Optional[ValidationResult]
    response: str
