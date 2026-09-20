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
    SubscriptionUpdate,
    SubscriptionDelete,
    ExpenseCategory,
)
from typing import Optional
from app.db.repository import (
    save_expense,
    get_expense,
    update_expenses,
    delete_expenses,
    get_subscription,
    save_subscription,
    update_subscriptions,
    delete_subscriptions,
    get_all_budgets,
    upsert_budget,
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
        return result


@tool
def get_subscription_tool(active_only: bool = True) -> list[dict]:
    """Get the user's subscriptions.

    Use this when the user wants to see, list, or check their subscriptions.
    By default, only active subscriptions are returned.
    Set active_only=False when the user asks for cancelled/inactive or all subscriptions.
    """

    try:
        subscriptions = get_subscription(active_only)
        print(f"[tool output] {len(subscriptions)} subscription(s) found")
        return subscriptions
    except Exception as e:
        result = f"Error fetching Subscriptions: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def update_subscription_tool(
    updates: list[SubscriptionUpdate],
):
    """
    Update one or more existing subscriptions.

    Use this tool only after identifying the existing subscription(s).
    The subscription_id must come from get_subscription_tool results.

    Do not ask the user for subscription_id.
    If the target subscription cannot be identified, use get_subscription_tool
    or ask the user for clarification.
    """
    try:
        updated_subscriptions = update_subscriptions(updates=updates)
        if not updated_subscriptions:
            result = "No subscriptions were found to update."
        else:
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
                for subscription in updated_subscriptions
            ]
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Failed to update subscriptions: {str(e)}"
        print(f"[tool output] {result}")
        return result


@tool(args_schema=SubscriptionDelete)
def delete_subscription_tool(subscription_ids: list[int]) -> str:
    """Delete one or more subscriptions by their IDs."""
    try:
        deleted = delete_subscriptions(subscription_ids=subscription_ids)
        result = f"Deleted {len(deleted)} subscription(s): {deleted}"
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error deleting subscriptions: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def set_budget_tool(
    category: ExpenseCategory | None = None, amount: float = 0.0
) -> str:
    """
    Set or update a monthly budget.

    Omit category (or pass null) to set the overall monthly budget across all spending.
    Pass a category to set a budget limit specific to that category (e.g. category="food").

    If a budget already exists for this category, it is replaced with the new amount —
    do not create duplicate budgets for the same category.
    """
    try:
        budget = upsert_budget(category=category, amount=amount, period="monthly")
        label = category.value if category else "overall"
        result = f"Set {label} monthly budget to {budget.amount}."
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error setting budget: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def get_budgets_tool() -> list[dict]:
    """Get all currently set budgets, including the overall budget if set."""
    try:
        budgets = get_all_budgets()
        print(f"[tool output] {len(budgets)} budget(s) found")
        return budgets
    except Exception as e:
        print(f"[tool output] Error fetching budgets: {e}")
        return []


tools = [
    create_expenses_tool,
    get_expenses_tool,
    update_expenses_tool,
    delete_expenses_tool,
    get_subscription_tool,
    create_subscription_tool,
    update_subscription_tool,
    delete_subscription_tool,
    set_budget_tool,
    get_budgets_tool,
]
