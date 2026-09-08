from typing import TypedDict, Optional, Literal, Annotated
from pydantic import BaseModel
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from datetime import date as dt

# --- Pydantic Models ---


class Expense(BaseModel):
    amount: float
    currency: Optional[str] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    date: Optional[dt] = None
    description: Optional[str] = None


class ExpenseQuery(BaseModel):
    start_date: Optional[dt] = None
    end_date: Optional[dt] = None
    merchant: list[str] = None
    category: list[str] = None
    subcategories: list[str] = []
    aggregation: Literal["list", "total", "count"] = "list"


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str]
    missing_fields: list[str]


class IntentClassification(BaseModel):
    intent: Literal["expense", "other", "query"]
    confidence: float


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class ChatResponse(BaseModel):
    response: str


# --- LangGraph State ---


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    intent: Literal["expense", "other", "query"]
    expense: Optional[Expense]
    validation_result: Optional[ValidationResult]
    clarification_round: int = 3
    response: str
    expense_query: Optional[ExpenseQuery]
    query_results: Optional[list[Expense]]
    query_response: Optional[str]
