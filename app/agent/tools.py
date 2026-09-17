from langchain_core.tools import tool
from app.agent.state import (
    ExpenseInput,
    CreateExpensesInput,
    ExpenseQuery,
    ExpenseResult,
)
from app.db.repository import save_expense, get_expense
from datetime import date as dt


@tool
def test_tool(value: str) -> str:
    """Test tool used to verify the agentic tool-calling loop."""
    return f"Test tool received: {value}"


@tool(args_schema=CreateExpensesInput)
def create_expenses(expenses: list[ExpenseInput]) -> str:
    """Create one or more expenses."""
    try:
        for expense in expenses:
            save_expense(expense)
        return f"Successfully created {len(expenses)} expense(s)."
    except Exception as e:
        return f"Error creating expense: {e}"


@tool(args_schema=ExpenseQuery)
def get_expenses(
    start_date: dt | None = None,
    end_date: dt | None = None,
    merchant: list[str] | None = None,
    category: list[str] | None = None,
    subcategories: list[str] | None = None,
    aggregation: str = "list",
) -> list[ExpenseResult]:
    """Fetch expenses from the database."""
    try:
        expense_query = ExpenseQuery(
            start_date=start_date,
            end_date=end_date,
            merchant=merchant,
            category=category,
            subcategories=subcategories,
            aggregation=aggregation,
        )

        expenses = get_expense(expense_query)

        results = [
            ExpenseResult(
                id=expense.id,
                amount=expense.amount,
                currency=expense.currency,
                merchant=expense.merchant,
                category=expense.category,
                subcategory=expense.subcategory,
                date=expense.date,
                description=expense.description,
            )
            for expense in expenses
        ]
        return results
    except Exception as e:
        return []


tools = [create_expenses, get_expenses]
