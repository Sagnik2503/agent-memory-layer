from typing import TypedDict, Annotated, Optional, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, field_validator, Field
from datetime import date as dt
from decimal import Decimal
from enum import Enum


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class ExpenseCategory(str, Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    SHOPPING = "shopping"
    BILLS = "bills"
    ENTERTAINMENT = "entertainment"
    HEALTH = "health"
    PERSONAL_CARE = "personal_care"
    OTHER = "other"


class SubscriptionFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ExpenseInput(BaseModel):
    amount: float
    currency: str | None = None
    merchant: str | None = None
    category: ExpenseCategory
    subcategory: str | None = None
    date: dt | None = None
    description: str | None = None


class ExpenseResult(BaseModel):
    id: int
    amount: float
    currency: str | None = None
    merchant: str | None = None
    category: ExpenseCategory
    subcategory: str | None = None
    date: dt | None = None
    description: str | None = None


class CreateExpensesInput(BaseModel):
    expenses: list[ExpenseInput]


class ExpenseQuery(BaseModel):
    start_date: Optional[dt] = None
    end_date: Optional[dt] = None
    merchant: Optional[list[str]] = None
    category: Optional[list[ExpenseCategory]] = None
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
    category: Optional[ExpenseCategory] = None
    subcategory: Optional[str] = None
    date: Optional[dt] = None
    description: Optional[str] = None


class ExpenseDelete(BaseModel):
    expense_ids: list[int]
    confirm: bool = False


class ChatRequest(BaseModel):
    message: str
    thread_id: str
    user_id: str | None = None


class ChatResponse(BaseModel):
    response: str


class SubscriptionResponse(BaseModel):
    id: int
    merchant: str
    amount: Decimal
    currency: str
    category: ExpenseCategory
    subcategory: str | None
    frequency: SubscriptionFrequency
    next_due_date: dt
    is_active: bool


class SubscriptionCreate(BaseModel):
    merchant: str
    amount: float
    currency: str = Field(default="INR")
    category: ExpenseCategory
    subcategory: str | None = None
    frequency: SubscriptionFrequency
    next_due_date: dt


class SubscriptionUpdate(BaseModel):
    subscription_id: int
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[ExpenseCategory] = None
    subcategory: Optional[str] = None
    frequency: Optional[SubscriptionFrequency] = None
    next_due_date: Optional[dt] = None
    is_active: Optional[bool] = None


class SubscriptionDelete(BaseModel):
    subscription_ids: list[int]
    confirm: bool = False


class CreateSubscriptionsInput(BaseModel):
    subscriptions: list[SubscriptionCreate]


class MonthlySummary(BaseModel):
    month: str  # "2026-09"
    total_spent: float
    total_transactions: int
    average_transaction: float
    top_category: str
    top_merchant: str
    currency: str


class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float
    transaction_count: int
    average_per_transaction: float


class BudgetStatus(BaseModel):
    category: str | None  # None = overall budget
    budget_amount: float
    spent_amount: float
    remaining: float
    percentage_used: float
    is_over_budget: bool


class SubscriptionSummary(BaseModel):
    total_monthly_cost: float
    active_count: int
    by_category: list[CategoryBreakdown]
    next_due_dates: list[dict]  # {merchant, amount, due_date}


class MonthComparison(BaseModel):
    current_month: MonthlySummary
    previous_month: MonthlySummary
    total_change: float
    total_change_percentage: float
    top_category_change: dict  # {category, change_amount, change_percentage}


class BudgetInput(BaseModel):
    category: str | None  # None = overall budget
    amount: float
    period: str  # "monthly"
