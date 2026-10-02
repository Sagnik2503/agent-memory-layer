from datetime import date
from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.agent.state import BudgetInput, ChatRequest, ChatResponse
from app.analytics import get_budget_status, get_category_breakdown
from langchain_core.messages import HumanMessage
from app.agent.graph import create_agent_graph
from app.config import DEFAULT_USER_ID
from app.db.database import Base, engine
from app.db.migrations import migrate_add_user_id
from app.db.repository import (
    get_budgets_for_period,
    get_expenses_for_month,
    get_subscriptions_due_within,
    to_expense_results,
    upcoming_bill,
)
from sqlalchemy.exc import SQLAlchemyError


def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        migrate_add_user_id(engine, DEFAULT_USER_ID)
    except SQLAlchemyError as e:
        print(f"[error] Failed to initialize database: {e}")


app = FastAPI()

init_db()

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _page(filename: str) -> FileResponse:
    return FileResponse(STATIC_DIR / filename, media_type="text/html")

try:
    expense_graph = create_agent_graph()
except Exception as e:
    print(f"[error] Failed to create agent graph: {e}")
    expense_graph = None


@app.get("/", response_class=HTMLResponse)
def dashboard_page():
    return _page("dashboard.html")


@app.get("/expenses", response_class=HTMLResponse)
def expenses_page():
    return _page("expenses.html")


@app.get("/budgets", response_class=HTMLResponse)
def budgets_page():
    return _page("budgets.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MONTH_PATTERN = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def _parse_month(month: str | None) -> str:
    month = month or date.today().strftime("%Y-%m")
    if not MONTH_PATTERN.fullmatch(month):
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
    return month


def _rows_for_month(month: str):
    year, month_num = (int(part) for part in month.split("-"))
    return get_expenses_for_month(DEFAULT_USER_ID, year, month_num)


def _group_by_currency(rows) -> dict[str, list]:
    """Group Expense rows by currency, defaulting a null currency to INR."""
    groups: dict[str, list] = {}
    for row in rows:
        groups.setdefault(row.currency or "INR", []).append(row)
    return groups


def _totals_by_currency(rows) -> dict[str, float]:
    """Group amounts by currency. Currencies are never summed together."""
    totals: dict[str, float] = {}
    for code, group in _group_by_currency(rows).items():
        totals[code] = sum(row.amount for row in group)
    return totals


def _expense_item(row) -> dict:
    """Display fields for one Expense row.

    Shared by GET /api/expenses and the dashboard's recent list so both
    surfaces render identical data.
    """
    return {
        "date": row.date.isoformat() if row.date else None,
        "merchant": row.merchant,
        "category": row.category,
        "subcategory": row.subcategory,
        "amount": row.amount,
        "currency": row.currency,
    }


RECENT_EXPENSES_LIMIT = 5


def _recent_expenses(rows) -> list[dict]:
    """The newest Expenses of the requested month, capped at
    RECENT_EXPENSES_LIMIT. Rows arrive newest-first from the repository."""
    return [_expense_item(row) for row in rows[:RECENT_EXPENSES_LIMIT]]


def _category_breakdown(rows) -> list[dict]:
    """Category breakdown for the month, measured per currency.

    `analytics.get_category_breakdown` sums amounts within the list it is
    given, so it runs once per currency group — the per-currency rule means
    amounts (and the percentages derived from them) are never combined across
    currencies. Labels come from the ExpenseCategory vocabulary through
    `to_expense_results`, so only canonical values can appear.
    """
    entries: list[dict] = []
    groups = _group_by_currency(rows)
    for code in sorted(groups):
        for item in get_category_breakdown(to_expense_results(groups[code])):
            entries.append({**item.model_dump(), "currency": code})
    return entries


UPCOMING_BILLS_DAYS = 7


def _upcoming_bills() -> list[dict]:
    """Subscriptions due within UPCOMING_BILLS_DAYS, overdue ones included and
    marked.

    Bills are anchored to today rather than the requested month: a
    Subscription's next due date is a point in time and the card answers
    "what is about to hit my account". The window and the shared
    `upcoming_bill` shape match the agent's get_upcoming_bills_tool, so the
    dashboard and chat never disagree.
    """
    today = date.today()
    return [
        upcoming_bill(s, today)
        for s in get_subscriptions_due_within(
            DEFAULT_USER_ID, within_days=UPCOMING_BILLS_DAYS
        )
    ]


BUDGET_CURRENCY = "INR"


def _budget_statuses(month: str) -> list[dict]:
    """Budget status for the requested month, for the Budgets page to reuse.

    Mirrors the agent's get_budget_status_tool: a Budget is a single-currency
    limit measured in BUDGET_CURRENCY, so only that currency's expenses count
    as spent — expenses in other currencies are excluded (per-currency rule).
    Category budgets come first (alphabetical), the overall Budget (no
    category) last, matching a totals row.
    """
    year, month_num = (int(part) for part in month.split("-"))
    budgets = [
        BudgetInput(category=b.category, amount=b.amount, period=b.period)
        for b in get_budgets_for_period(DEFAULT_USER_ID, "monthly")
    ]
    expenses = to_expense_results(
        get_expenses_for_month(DEFAULT_USER_ID, year, month_num, BUDGET_CURRENCY)
    )
    statuses = get_budget_status(budgets, expenses)
    statuses.sort(key=lambda s: (s.category is None, s.category or ""))
    return [
        {**status.model_dump(), "currency": BUDGET_CURRENCY}
        for status in statuses
    ]


@app.get("/api/expenses")
def list_expenses(month: str | None = None):
    month = _parse_month(month)
    rows = _rows_for_month(month)
    return {
        "month": month,
        "items": [_expense_item(row) for row in rows],
        "totals_by_currency": _totals_by_currency(rows),
    }


@app.get("/api/dashboard")
def dashboard_summary(month: str | None = None):
    """Monthly summary for the requested month, defaulting to the current month."""
    month = _parse_month(month)
    rows = _rows_for_month(month)
    return {
        "month": month,
        "totals_by_currency": _totals_by_currency(rows),
        "category_breakdown": _category_breakdown(rows),
        "budget_statuses": _budget_statuses(month),
        "upcoming_bills": _upcoming_bills(),
        "recent_expenses": _recent_expenses(rows),
    }


@app.get("/health")
async def health():
    return {"status": "Application is running"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if expense_graph is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        config = {
            "configurable": {
                "thread_id": request.thread_id,
                "user_id": request.user_id or DEFAULT_USER_ID,
            }
        }

        result = expense_graph.invoke(
            {"messages": [HumanMessage(content=request.message)]},
            config=config,
        )

        ai_message = result["messages"][-1]

        if isinstance(ai_message.content, list):
            text_parts = [
                b["text"] for b in ai_message.content if b.get("type") == "text"
            ]
            return ChatResponse(response="\n".join(text_parts))

        return ChatResponse(response=ai_message.content)
    except Exception as e:
        print(f"[error] Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process chat message")
