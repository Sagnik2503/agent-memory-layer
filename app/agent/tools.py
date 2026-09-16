from langchain_core.tools import tool
from app.agent.state import ExpenseInput, CreateExpensesInput
from app.db.repository import save_expense


@tool
def test_tool(value: str) -> str:
    """Test tool used to verify the agentic tool-calling loop."""
    return f"Test tool received: {value}"


@tool(args_schema=CreateExpensesInput)
def create_expenses(expenses: list[ExpenseInput]) -> str:
    """Create one or more expenses."""

    saved_expenses = []
    try:
        for expense in expenses:
            saved_expenses.append(save_expense(expense))
        return f"Successfully created {len(saved_expenses)} expense(s)."
    except Exception as e:
        print(f"could not creat a new expense: {e}")


tools = [create_expenses]
