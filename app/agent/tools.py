from langchain_core.tools import tool
from app.agent.state import (
    ExpenseInput,
    CreateExpensesInput,
    ExpenseQuery,
    ExpenseResult,
    ExpenseUpdate,
    ExpenseDelete,
    CreateSubscriptionsInput,
    SubscriptionCreate,
    SubscriptionResponse,
)
from typing import Optional
from app.db.repository import (
    save_expense,
    get_expense,
    update_expenses,
    delete_expenses,
    get_subscription,
    save_subscription,
)
from datetime import date as dt


@tool(args_schema=CreateExpensesInput)
def create_expenses_tool(expenses: list[ExpenseInput]) -> str:
    """Create one or more expenses."""
    try:
        for expense in expenses:
            save_expense(expense)
        result = f"Successfully created {len(expenses)} expense(s)."
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error creating expense: {e}"
        print(f"[tool output] {result}")
        return result


@tool(args_schema=ExpenseQuery)
def get_expenses_tool(
    start_date: dt | None = None,
    end_date: dt | None = None,
    merchant: list[str] | None = None,
    category: list[str] | None = None,
    subcategories: list[str] | None = None,
    aggregation: str = "list",
) -> list[ExpenseResult]:
    """
    Retrieve existing expenses from the database.

    Use this tool when:
    - the user asks to view expenses
    - you need to find an expense before updating it
    - you need to identify which existing expense the user means
    """
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
        print(f"[tool output] {len(results)} expense(s) found")
        return results
    except Exception as e:
        print(f"[tool output] Error fetching expenses: {e}")
        return []


@tool
def update_expenses_tool(
    updates: list[ExpenseUpdate],
):
    """
    Update one or more existing expenses.

    Use this tool only after identifying the existing expense(s).
    The expense_id must come from get_expenses_tool results.

    Do not ask the user for expense_id.
    If the target expense cannot be identified, use get_expenses_tool
    or ask the user for clarification.
    """
    try:
        updated_expenses = update_expenses(updates=updates)
        if not update_expenses:
            result = "No expenses were found to update."
        else:
            result = str(updated_expenses)
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Failed to update expenses: {str(e)}"
        print(f"[tool output] {result}")
        return result


@tool(args_schema=ExpenseDelete)
def delete_expenses_tool(expense_ids: list[int]) -> str:
    """Delete one or more expenses by their IDs."""
    try:
        deleted = delete_expenses(expense_ids=expense_ids)
        result = f"Deleted {len(deleted)} expense(s): {deleted}"
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error deleting expenses: {e}"
        print(f"[tool output] {result}")
        return result


@tool(args_schema=CreateSubscriptionsInput)
def create_subscription_tool(
    subscriptions: list[SubscriptionCreate],
) -> list[SubscriptionResponse]:
    """Create one or more recurring subscriptions for the user.

    Use this for adding new subscriptions. Returns the created subscriptions.
    Do not use for one-time expenses.
    """
    try:
        created_subscriptions = save_subscription(subscriptions)
        result = [
            SubscriptionResponse(
                id=subscription.id,
                merchant=subscription.merchant,
                amount=subscription.amount,
                currency=subscription.currency,
                category=subscription.category,
                subcategory=subscription.subcategory,
                frequency=subscription.frequency,
                next_due_date=subscription.next_due_date,
                is_active=subscription.is_active,
            )
            for subscription in created_subscriptions
        ]
        print(f"[tool output] Successfully created {len(result)} subscription(s).")
        return result

    except Exception as e:
        result = f"Failed to create subscriptions: {e}"
        print(f"[tool output] {result}")
        raise RuntimeError(result)


@tool
def get_subscription_tool(active_only: bool = True) -> list[dict]:
    """Get the user's subscriptions.

    Use this when the user wants to see, list, or check their subscriptions.
    By default, only active subscriptions are returned.
    Set active_only=False when the user asks for cancelled/inactive or all subscriptions.
    """

    subscriptions: list = []
    try:
        subscriptions = get_subscription(active_only)
        print(f"[tool output] {len(subscriptions)} subscription(s) found")
        if not subscriptions:
            return "No subscriptions found."
        return subscriptions
    except Exception as e:
        result = f"Error fetching Subscriptions: {e}"
        print(f"[tool output] {result}")
        return result


tools = [
    create_expenses_tool,
    get_expenses_tool,
    update_expenses_tool,
    delete_expenses_tool,
    get_subscription_tool,
    create_subscription_tool,
]
