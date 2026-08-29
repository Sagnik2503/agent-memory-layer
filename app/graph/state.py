from typing import TypedDict, Optional, Literal, Annotated
from pydantic import BaseModel
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


# --- Pydantic Models ---


class Expense(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    missing_fields: list[str]


class IntentClassification(BaseModel):
    intent: Literal["expense", "other"]
    confidence: float


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class ChatResponse(BaseModel):
    response: str


# --- LangGraph State ---


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Literal["expense", "other"]
    expense: Optional[Expense]
    validation_result: Optional[ValidationResult]
    clarification_round: int = 3
    response: str

