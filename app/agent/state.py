from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from datetime import date as dt


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


class CreateExpensesInput(BaseModel):
    expenses: list[ExpenseInput]
