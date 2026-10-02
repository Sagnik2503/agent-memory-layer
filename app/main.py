from datetime import date
from pathlib import Path
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.agent.state import ChatRequest, ChatResponse
from langchain_core.messages import HumanMessage
from app.agent.graph import create_agent_graph
from app.config import DEFAULT_USER_ID
from app.db.database import Base, engine
from app.db.migrations import migrate_add_user_id
from app.db.repository import get_expenses_for_month
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


@app.get("/api/expenses")
def list_expenses(month: str | None = None):
    month = month or date.today().strftime("%Y-%m")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise HTTPException(status_code=400, detail="month must be in YYYY-MM format")
    year, month_num = (int(part) for part in month.split("-"))
    rows = get_expenses_for_month(DEFAULT_USER_ID, year, month_num)
    totals_by_currency: dict[str, float] = {}
    items = []
    for row in rows:
        totals_by_currency[row.currency or "INR"] = (
            totals_by_currency.get(row.currency or "INR", 0.0) + row.amount
        )
        items.append(
            {
                "date": row.date.isoformat() if row.date else None,
                "merchant": row.merchant,
                "category": row.category,
                "subcategory": row.subcategory,
                "amount": row.amount,
                "currency": row.currency,
            }
        )
    return {
        "month": month,
        "items": items,
        "totals_by_currency": totals_by_currency,
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
