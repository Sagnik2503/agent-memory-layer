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
    MonthlySummary,
    CategoryBreakdown,
    BudgetStatus,
    SubscriptionSummary,
    MonthComparison,
    BudgetInput,
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
    get_expenses_for_month,
    get_budgets_for_period,
)
from app.analytics import (
    get_monthly_summary,
    get_category_breakdown,
    get_budget_status,
    get_subscription_summary,
    compare_months,
    get_spending_by_merchant,
)
from datetime import date, datetime as dt


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


@tool
def get_monthly_summary_tool(
    month: str | None = None,
    currency: str = "INR"
) -> MonthlySummary:
    """Get spending summary for a specific month.
    
    Use when user asks: 'How much did I spend this month?', 'Monthly summary', 'What's my spending for September?'
    """
    try:
        if month is None:
            month = date.today().strftime("%Y-%m")
        
        year, month_num = map(int, month.split("-"))
        expenses = get_expenses_for_month(year, month_num, currency)
        
        expense_results = [
            ExpenseResult(
                id=e.id,
                amount=e.amount,
                currency=e.currency,
                merchant=e.merchant,
                category=e.category,
                subcategory=e.subcategory,
                date=e.date,
                description=e.description,
            )
            for e in expenses
        ]
        
        summary = get_monthly_summary(expense_results, month, currency)
        print(f"[tool output] Monthly summary: {summary.total_spent} total spent")
        return summary
    except Exception as e:
        result = f"Error getting monthly summary: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def get_category_breakdown_tool(
    month: str | None = None,
    currency: str = "INR"
) -> list[CategoryBreakdown]:
    """Get spending breakdown by category.
    
    Use when user asks: 'Where did I spend the most?', 'Show category breakdown', 'What categories am I spending on?'
    """
    try:
        if month is None:
            month = date.today().strftime("%Y-%m")
        
        year, month_num = map(int, month.split("-"))
        expenses = get_expenses_for_month(year, month_num, currency)
        
        expense_results = [
            ExpenseResult(
                id=e.id,
                amount=e.amount,
                currency=e.currency,
                merchant=e.merchant,
                category=e.category,
                subcategory=e.subcategory,
                date=e.date,
                description=e.description,
            )
            for e in expenses
        ]
        
        breakdown = get_category_breakdown(expense_results)
        print(f"[tool output] {len(breakdown)} categories found")
        return breakdown
    except Exception as e:
        result = f"Error getting category breakdown: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def get_budget_status_tool() -> list[BudgetStatus]:
    """Get status of all budgets vs actual spending.
    
    Use when user asks: 'How am I doing on my budgets?', 'Am I over budget?', 'Budget status'
    """
    try:
        today = date.today()
        
        budgets_db = get_budgets_for_period("monthly")
        budgets = [
            BudgetInput(
                category=b.category,
                amount=b.amount,
                period=b.period,
            )
            for b in budgets_db
        ]
        
        expenses = get_expenses_for_month(today.year, today.month)
        
        expense_results = [
            ExpenseResult(
                id=e.id,
                amount=e.amount,
                currency=e.currency,
                merchant=e.merchant,
                category=e.category,
                subcategory=e.subcategory,
                date=e.date,
                description=e.description,
            )
            for e in expenses
        ]
        
        status = get_budget_status(budgets, expense_results)
        print(f"[tool output] {len(status)} budgets checked")
        return status
    except Exception as e:
        result = f"Error getting budget status: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def get_subscription_summary_tool() -> SubscriptionSummary:
    """Get summary of all active subscriptions.
    
    Use when user asks: 'How much am I spending on subscriptions?', 'Subscription summary', 'What are my recurring costs?'
    """
    try:
        subscriptions = get_subscription(active_only=True)
        summary = get_subscription_summary(subscriptions)
        print(f"[tool output] {summary.active_count} active subscriptions, {summary.total_monthly_cost} monthly cost")
        return summary
    except Exception as e:
        result = f"Error getting subscription summary: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def compare_months_tool(
    month1: str,
    month2: str
) -> MonthComparison:
    """Compare spending between two months.
    
    Use when user asks: 'Compare this month to last month', 'How does September compare to August?'
    """
    try:
        # Get month 1 data
        year1, month_num1 = map(int, month1.split("-"))
        expenses1 = get_expenses_for_month(year1, month_num1)
        expense_results1 = [
            ExpenseResult(
                id=e.id,
                amount=e.amount,
                currency=e.currency,
                merchant=e.merchant,
                category=e.category,
                subcategory=e.subcategory,
                date=e.date,
                description=e.description,
            )
            for e in expenses1
        ]
        summary1 = get_monthly_summary(expense_results1, month1)
        
        # Get month 2 data
        year2, month_num2 = map(int, month2.split("-"))
        expenses2 = get_expenses_for_month(year2, month_num2)
        expense_results2 = [
            ExpenseResult(
                id=e.id,
                amount=e.amount,
                currency=e.currency,
                merchant=e.merchant,
                category=e.category,
                subcategory=e.subcategory,
                date=e.date,
                description=e.description,
            )
            for e in expenses2
        ]
        summary2 = get_monthly_summary(expense_results2, month2)
        
        comparison = compare_months(summary1, summary2)
        print(f"[tool output] Comparison: {comparison.total_change} change ({comparison.total_change_percentage}%)")
        return comparison
    except Exception as e:
        result = f"Error comparing months: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def get_spending_by_merchant_tool(
    month: str | None = None,
    top_n: int = 5
) -> list[dict]:
    """Get top merchants by spending.
    
    Use when user asks: 'Where do I spend the most?', 'Top merchants', 'Biggest expenses'
    """
    try:
        if month is None:
            month = date.today().strftime("%Y-%m")
        
        year, month_num = map(int, month.split("-"))
        expenses = get_expenses_for_month(year, month_num)
        
        expense_results = [
            ExpenseResult(
                id=e.id,
                amount=e.amount,
                currency=e.currency,
                merchant=e.merchant,
                category=e.category,
                subcategory=e.subcategory,
                date=e.date,
                description=e.description,
            )
            for e in expenses
        ]
        
        merchants = get_spending_by_merchant(expense_results, top_n)
        print(f"[tool output] {len(merchants)} top merchants found")
        return merchants
    except Exception as e:
        result = f"Error getting spending by merchant: {e}"
        print(f"[tool output] {result}")
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
    get_monthly_summary_tool,
    get_category_breakdown_tool,
    get_budget_status_tool,
    get_subscription_summary_tool,
    compare_months_tool,
    get_spending_by_merchant_tool,
]
