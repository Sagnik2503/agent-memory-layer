from typing import TypedDict, Annotated, Optional, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, field_validator, Field
from datetime import date as dt
from decimal import Decimal


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class ExpenseInput(BaseModel):
    amount: float
    currency: str | None = None
    merchant: str | None = None
    category: str | None = None
    subcategory: str | None = None
    date: dt | None = None
    description: str | None = None


class ExpenseResult(BaseModel):
    id: int
    amount: float
    currency: str | None = None
    merchant: str | None = None
    category: str | None = None
    subcategory: str | None = None
    date: dt | None = None
    description: str | None = None


class CreateExpensesInput(BaseModel):
    expenses: list[ExpenseInput]


class ExpenseQuery(BaseModel):
    start_date: Optional[dt] = None
    end_date: Optional[dt] = None
    merchant: Optional[list[str]] = None
    category: Optional[list[str]] = None
    subcategories: list[str] = []
    aggregation: Literal["list", "total", "count"] = "list"

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if v is None:
            return None
        if isinstance(v, dt):
            return v
        if isinstance(v, str):
            return dt.fromisoformat(v)
        return v


class ExpenseUpdate(BaseModel):
    expense_id: int
    amount: Optional[float] = None
    currency: Optional[str] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    date: Optional[dt] = None
    description: Optional[str] = None


class ExpenseDelete(BaseModel):
    expense_ids: list[int]


class ChatRequest(BaseModel):
    message: str
    thread_id: str


class ChatResponse(BaseModel):
    response: str


class SubscriptionResponse(BaseModel):
    id: int
    merchant: str
    amount: Decimal
    currency: str
    category: str
    subcategory: str | None
    frequency: str
    next_due_date: dt
    is_active: bool


class SubscriptionCreate(BaseModel):
    merchant: str
    amount: float
    currency: str = Field(default="INR")
    category: str
    subcategory: str | None = None
    frequency: str
    next_due_date: dt


class SubscriptionUpdate(BaseModel):
    subscription_id: int
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    frequency: Optional[str] = None
    next_due_date: Optional[dt] = None
    is_active: Optional[bool] = None


class SubscriptionDelete(BaseModel):
    subscription_ids: list[int]


class CreateSubscriptionsInput(BaseModel):
    subscriptions: list[SubscriptionCreate]
