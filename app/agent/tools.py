from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from app.config import DEFAULT_USER_ID
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
    get_expenses_by_ids,
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
    get_due_subscriptions,
    get_subscriptions_due_within,
    advance_subscription_due_date,
    advance_due_date,
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


def _user_id(config: RunnableConfig | None) -> str:
    if config:
        uid = (config.get("configurable") or {}).get("user_id")
        if uid:
            return str(uid)
    return DEFAULT_USER_ID


def _freq_str(frequency) -> str:
    return frequency.value if hasattr(frequency, "value") else str(frequency)


def _db_to_expense_results(expenses) -> list[ExpenseResult]:
    """Convert database expense objects to ExpenseResult models."""
    return [
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


def _group_by_currency(expenses: list[ExpenseResult]) -> dict[str, list[ExpenseResult]]:
    groups: dict[str, list[ExpenseResult]] = {}
    for e in expenses:
        groups.setdefault(e.currency or "INR", []).append(e)
    return groups


def _mixed_currency_message(groups: dict[str, list[ExpenseResult]]) -> str:
    parts = []
    for curr, items in sorted(groups.items()):
        total = sum(e.amount for e in items)
        parts.append(f"{curr}: {total:,.2f} ({len(items)} transaction(s))")
    return (
        "MIXED CURRENCIES — do not add amounts across currencies. "
        "Per-currency totals: " + "; ".join(parts) + ". "
        "Report each currency separately or ask the user which currency to focus on."
    )


def _expense_preview(expenses: list[ExpenseResult]) -> str:
    lines = []
    for e in expenses:
        curr = f"{e.currency} " if e.currency else ""
        cat = e.category.value if e.category else "n/a"
        lines.append(
            f"  id={e.id} | {e.date or 'no date'} | {e.merchant or 'unknown merchant'}"
            f" | {cat} | {curr}{e.amount:,.2f} | {e.description or ''}"
        )
    return "\n".join(lines)


def _update_preview(current: list[ExpenseResult], updates: list[ExpenseUpdate]) -> str:
    by_id = {e.id: e for e in current}
    lines = []
    for u in updates:
        cur = by_id.get(u.expense_id)
        if not cur:
            lines.append(f"  id={u.expense_id}: NOT FOUND (would be skipped)")
            continue
        changes = u.model_dump(exclude={"expense_id"}, exclude_none=True)
        if not changes:
            lines.append(f"  id={u.expense_id}: no changes specified")
            continue
        change_parts = []
        for field, new_value in changes.items():
            old_value = getattr(cur, field, None)
            if hasattr(old_value, "value"):
                old_value = old_value.value
            change_parts.append(f"{field}: {old_value!r} -> {new_value!r}")
        label = f"{cur.merchant or 'unknown'}, {cur.date or 'no date'}"
        lines.append(f"  id={u.expense_id} ({label}): " + "; ".join(change_parts))
    return "\n".join(lines)


def _budget_warnings(user_id: str) -> list[str]:
    """Current-month budget warnings after a spending change."""
    try:
        today = date.today()
        budgets_db = get_budgets_for_period(user_id, "monthly")
        if not budgets_db:
            return []
        budgets = [
            BudgetInput(category=b.category, amount=b.amount, period=b.period)
            for b in budgets_db
        ]
        expenses = _db_to_expense_results(
            get_expenses_for_month(user_id, today.year, today.month)
        )
        warnings = []
        for status in get_budget_status(budgets, expenses):
            label = status.category or "overall"
            if status.is_over_budget:
                over = status.spent_amount - status.budget_amount
                warnings.append(
                    f"BUDGET EXCEEDED [{label}]: spent {status.spent_amount:,.2f} "
                    f"of {status.budget_amount:,.2f} ({over:,.2f} over)."
                )
            elif status.percentage_used >= 80:
                warnings.append(
                    f"BUDGET WARNING [{label}]: {status.percentage_used:.0f}% used "
                    f"({status.spent_amount:,.2f} of {status.budget_amount:,.2f})."
                )
        return warnings
    except Exception:
        return []


@tool(args_schema=CreateExpensesInput)
def create_expenses_tool(
    expenses: list[ExpenseInput], config: RunnableConfig = None
) -> str:
    """Create one or more expenses.

    Currency defaults to INR when omitted. Date defaults to today when omitted
    (always pass a date for past expenses so monthly reports stay accurate).
    """
    try:
        uid = _user_id(config)
        for expense in expenses:
            if not expense.currency:
                expense = expense.model_copy(update={"currency": "INR"})
            if not expense.date:
                expense = expense.model_copy(update={"date": date.today()})
            save_expense(uid, expense)
        result = f"Successfully created {len(expenses)} expense(s)."
        warnings = _budget_warnings(uid)
        if warnings:
            result += "\n" + "\n".join(warnings)
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
    config: RunnableConfig = None,
) -> list[ExpenseResult]:
    """
    Retrieve existing expenses from the database.

    Use this tool when:
    - the user asks to view expenses
    - you need to find an expense before updating or deleting it
    - you need to identify which existing expense the user means

    If several expenses match an ambiguous reference, return them all and ask
    the user which one they mean. Never guess an expense_id.
    """
    try:
        uid = _user_id(config)
        expense_query = ExpenseQuery(
            start_date=start_date,
            end_date=end_date,
            merchant=merchant,
            category=category,
            subcategories=subcategories,
            aggregation=aggregation,
        )

        expenses = get_expense(uid, expense_query)

        results = _db_to_expense_results(expenses)
        print(f"[tool output] {len(results)} expense(s) found")
        return results
    except Exception as e:
        print(f"[tool output] Error fetching expenses: {e}")
        return []


@tool
def update_expenses_tool(
    updates: list[ExpenseUpdate],
    confirm: bool = False,
    config: RunnableConfig = None,
) -> str:
    """
    Update one or more existing expenses.

    Two-phase: first call with confirm=false to preview the changes, show the
    preview to the user, and only call again with confirm=true after the user
    explicitly confirms. Keep the updates identical between the two calls.

    Use this tool only after identifying the existing expense(s) via
    get_expenses_tool. Never ask the user for expense_id; if the target cannot
    be identified, use get_expenses_tool or ask for clarification.
    """
    try:
        uid = _user_id(config)
        ids = [u.expense_id for u in updates]
        current = get_expenses_by_ids(uid, ids)

        if not confirm:
            if not current:
                return (
                    "PREVIEW FAILED: no expenses matched the given ids "
                    f"({ids}). Call get_expenses_tool to find the correct "
                    "expense before updating."
                )
            preview = _update_preview(current, updates)
            return (
                "CONFIRMATION REQUIRED — proposed changes (not applied yet):\n"
                f"{preview}\n"
                "Show this preview to the user and ask for confirmation. "
                "If the user confirms, call update_expenses_tool again with "
                "confirm=true and the exact same updates."
            )

        updated_expenses = update_expenses(uid, updates=updates)
        not_found = set(ids) - {e.id for e in updated_expenses}
        if not updated_expenses:
            result = "No expenses were found to update."
        else:
            result = f"Updated {len(updated_expenses)} expense(s):\n{_expense_preview(_db_to_expense_results(updated_expenses))}"
        if not_found:
            result += f"\nNot found (skipped): {sorted(not_found)}"
        warnings = _budget_warnings(uid)
        if warnings:
            result += "\n" + "\n".join(warnings)
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Failed to update expenses: {str(e)}"
        print(f"[tool output] {result}")
        return result


@tool(args_schema=ExpenseDelete)
def delete_expenses_tool(
    expense_ids: list[int],
    confirm: bool = False,
    config: RunnableConfig = None,
) -> str:
    """Delete one or more expenses by their IDs.

    Two-phase: first call with confirm=false to preview the records that would
    be deleted, show the preview to the user, and only call again with
    confirm=true after the user explicitly confirms. Keep expense_ids
    identical between the two calls. Always identify the expense(s) with
    get_expenses_tool first.
    """
    try:
        uid = _user_id(config)

        if not confirm:
            current = get_expenses_by_ids(uid, expense_ids)
            if not current:
                return (
                    "PREVIEW FAILED: no expenses matched the given ids "
                    f"({expense_ids}). Call get_expenses_tool to find the "
                    "correct expense before deleting."
                )
            preview = _expense_preview(current)
            return (
                "CONFIRMATION REQUIRED — these expenses would be permanently "
                "deleted (nothing deleted yet):\n"
                f"{preview}\n"
                "Show this preview to the user and ask for confirmation. If "
                "the user confirms, call delete_expenses_tool again with "
                "confirm=true and the exact same expense_ids."
            )

        deleted = delete_expenses(uid, expense_ids=expense_ids)
        not_found = set(expense_ids) - set(deleted)
        result = f"Deleted {len(deleted)} expense(s): {deleted}"
        if not_found:
            result += f"\nNot found (skipped): {sorted(not_found)}"
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error deleting expenses: {e}"
        print(f"[tool output] {result}")
        return result


@tool(args_schema=CreateSubscriptionsInput)
def create_subscription_tool(
    subscriptions: list[SubscriptionCreate],
    config: RunnableConfig = None,
) -> list[SubscriptionResponse]:
    """Create one or more recurring subscriptions for the user.

    Use this for adding new subscriptions. Returns the created subscriptions.
    Do not use for one-time expenses.
    """
    try:
        uid = _user_id(config)
        created_subscriptions = save_subscription(uid, subscriptions)
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
def get_subscription_tool(
    active_only: bool = True, config: RunnableConfig = None
) -> list[SubscriptionResponse]:
    """Get the user's subscriptions.

    Use this when the user wants to see, list, or check their subscriptions.
    By default, only active subscriptions are returned.
    Set active_only=False when the user asks for cancelled/inactive or all subscriptions.

    If several subscriptions match an ambiguous reference, return them all and
    ask the user which one they mean. Never guess a subscription_id.
    """

    try:
        uid = _user_id(config)
        subscriptions = get_subscription(uid, active_only)
        print(f"[tool output] {len(subscriptions)} subscription(s) found")
        return subscriptions
    except Exception as e:
        result = f"Error fetching Subscriptions: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def update_subscription_tool(
    updates: list[SubscriptionUpdate],
    confirm: bool = False,
    config: RunnableConfig = None,
) -> str:
    """
    Update one or more existing subscriptions.

    Two-phase: first call with confirm=false to preview the changes, show the
    preview to the user, and only call again with confirm=true after the user
    explicitly confirms. Keep the updates identical between the two calls.

    Use this tool only after identifying the existing subscription(s) via
    get_subscription_tool. Never ask the user for subscription_id.
    """
    try:
        uid = _user_id(config)
        if not confirm:
            all_subs = get_subscription(uid, active_only=False)
            wanted = {u.subscription_id for u in updates}
            current = [s for s in all_subs if s.id in wanted]
            if not current:
                return (
                    "PREVIEW FAILED: no subscriptions matched the given ids. "
                    "Call get_subscription_tool to find the correct "
                    "subscription before updating."
                )
            lines = []
            for u in updates:
                cur = next((s for s in current if s.id == u.subscription_id), None)
                if not cur:
                    lines.append(
                        f"  id={u.subscription_id}: NOT FOUND (would be skipped)"
                    )
                    continue
                changes = u.model_dump(
                    exclude={"subscription_id"}, exclude_none=True
                )
                if not changes:
                    lines.append(f"  id={u.subscription_id}: no changes specified")
                    continue
                parts = []
                for field, new_value in changes.items():
                    old_value = getattr(cur, field, None)
                    if hasattr(old_value, "value"):
                        old_value = old_value.value
                    parts.append(f"{field}: {old_value!r} -> {new_value!r}")
                lines.append(f"  id={u.subscription_id} ({cur.merchant}): " + "; ".join(parts))
            return (
                "CONFIRMATION REQUIRED — proposed subscription changes (not "
                "applied yet):\n"
                + "\n".join(lines)
                + "\nShow this preview to the user and ask for confirmation. "
                "If the user confirms, call update_subscription_tool again "
                "with confirm=true and the exact same updates."
            )

        updated_subscriptions = update_subscriptions(uid, updates=updates)
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
def delete_subscription_tool(
    subscription_ids: list[int],
    confirm: bool = False,
    config: RunnableConfig = None,
) -> str:
    """Delete one or more subscriptions by their IDs.

    Two-phase: first call with confirm=false to preview the records that would
    be deleted, show the preview to the user, and only call again with
    confirm=true after the user explicitly confirms. Keep subscription_ids
    identical between the two calls. Identify the subscription(s) with
    get_subscription_tool first.
    """
    try:
        uid = _user_id(config)

        if not confirm:
            all_subs = get_subscription(uid, active_only=False)
            wanted = {s for s in subscription_ids}
            current = [s for s in all_subs if s.id in wanted]
            if not current:
                return (
                    "PREVIEW FAILED: no subscriptions matched the given ids "
                    f"({subscription_ids}). Call get_subscription_tool to find "
                    "the correct subscription before deleting."
                )
            lines = [
                f"  id={s.id} | {s.merchant} | {s.currency} {float(s.amount):,.2f}"
                f" | { _freq_str(s.frequency) } | next due {s.next_due_date}"
                for s in current
            ]
            return (
                "CONFIRMATION REQUIRED — these subscriptions would be "
                "permanently deleted (nothing deleted yet):\n"
                + "\n".join(lines)
                + "\nShow this preview to the user and ask for confirmation. "
                "If the user confirms, call delete_subscription_tool again "
                "with confirm=true and the exact same subscription_ids."
            )

        deleted = delete_subscriptions(uid, subscription_ids=subscription_ids)
        not_found = set(subscription_ids) - set(deleted)
        result = f"Deleted {len(deleted)} subscription(s): {deleted}"
        if not_found:
            result += f"\nNot found (skipped): {sorted(not_found)}"
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error deleting subscriptions: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def set_budget_tool(
    category: ExpenseCategory | None = None,
    amount: float = 0.0,
    config: RunnableConfig = None,
) -> str:
    """
    Set or update a monthly budget.

    Omit category (or pass null) to set the overall monthly budget across all spending.
    Pass a category to set a budget limit specific to that category (e.g. category="food").

    If a budget already exists for this category, it is replaced with the new amount —
    do not create duplicate budgets for the same category.

    Budgets are single-currency limits expressed in the user's main currency (INR by default).
    """
    try:
        uid = _user_id(config)
        budget = upsert_budget(uid, category=category, amount=amount, period="monthly")
        label = category.value if category else "overall"
        result = f"Set {label} monthly budget to {budget.amount}."
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error setting budget: {e}"
        print(f"[tool output] {result}")
        return result


@tool
def get_budgets_tool(config: RunnableConfig = None) -> list[dict]:
    """Get all currently set budgets, including the overall budget if set."""
    try:
        uid = _user_id(config)
        budgets = get_all_budgets(uid)
        print(f"[tool output] {len(budgets)} budget(s) found")
        return budgets
    except Exception as e:
        print(f"[tool output] Error fetching budgets: {e}")
        return []


@tool
def get_monthly_summary_tool(
    month: str | None = None,
    currency: str | None = None,
    config: RunnableConfig = None,
) -> MonthlySummary | str:
    """Get spending summary for a specific month.

    Use when user asks: 'How much did I spend this month?', 'Monthly summary',
    'What's my spending for September?'

    month format: "YYYY-MM". currency filters to a single currency (e.g. "INR",
    "USD"); omit for all currencies. If the month contains mixed currencies a
    per-currency breakdown is returned instead of a single total — never sum
    across currencies.
    """
    try:
        uid = _user_id(config)
        if month is None:
            month = date.today().strftime("%Y-%m")

        year, month_num = map(int, month.split("-"))
        expenses = _db_to_expense_results(
            get_expenses_for_month(uid, year, month_num, currency)
        )

        if not expenses:
            return MonthlySummary(
                month=month,
                total_spent=0,
                total_transactions=0,
                average_transaction=0,
                top_category="N/A",
                top_merchant="N/A",
                currency=currency or "INR",
            )

        groups = _group_by_currency(expenses)
        if len(groups) > 1:
            return f"Summary for {month}: " + _mixed_currency_message(groups)

        result_currency = next(iter(groups))
        summary = get_monthly_summary(expenses, month, result_currency)
        print(f"[tool output] Monthly summary: {summary.total_spent} total spent")
        return summary
    except Exception as e:
        result = f"Error getting monthly summary: {e}"
        print(f"[tool output] {result}")
        return MonthlySummary(
            month=month or "",
            total_spent=0,
            total_transactions=0,
            average_transaction=0,
            top_category="N/A",
            top_merchant="N/A",
            currency=currency or "INR",
        )


@tool
def get_category_breakdown_tool(
    month: str | None = None,
    currency: str | None = None,
    config: RunnableConfig = None,
) -> list[CategoryBreakdown] | str:
    """Get spending breakdown by category.

    Use when user asks: 'Where did I spend the most?', 'Show category breakdown',
    'What categories am I spending on?'

    month format: "YYYY-MM". currency filters to a single currency; omit for all
    currencies. Mixed-currency months return a per-currency note instead.
    """
    try:
        uid = _user_id(config)
        if month is None:
            month = date.today().strftime("%Y-%m")

        year, month_num = map(int, month.split("-"))
        expenses = _db_to_expense_results(
            get_expenses_for_month(uid, year, month_num, currency)
        )

        if not expenses:
            return []

        groups = _group_by_currency(expenses)
        if len(groups) > 1:
            return f"Breakdown for {month}: " + _mixed_currency_message(groups)

        breakdown = get_category_breakdown(expenses)
        print(f"[tool output] {len(breakdown)} categories found")
        return breakdown
    except Exception as e:
        result = f"Error getting category breakdown: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def get_budget_status_tool(
    currency: str = "INR", config: RunnableConfig = None
) -> list[BudgetStatus]:
    """Get status of all budgets vs actual spending.

    Use when user asks: 'How am I doing on my budgets?', 'Am I over budget?', 'Budget status'

    Budgets are single-currency limits; spending is measured in that same
    currency (INR by default), so expenses in other currencies are excluded.
    """
    try:
        uid = _user_id(config)
        today = date.today()

        budgets_db = get_budgets_for_period(uid, "monthly")
        budgets = [
            BudgetInput(
                category=b.category,
                amount=b.amount,
                period=b.period,
            )
            for b in budgets_db
        ]

        expenses = _db_to_expense_results(
            get_expenses_for_month(uid, today.year, today.month, currency)
        )

        status = get_budget_status(budgets, expenses)
        print(f"[tool output] {len(status)} budgets checked")
        return status
    except Exception as e:
        result = f"Error getting budget status: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def get_subscription_summary_tool(
    config: RunnableConfig = None,
) -> SubscriptionSummary:
    """Get summary of all active subscriptions.

    Use when user asks: 'How much am I spending on subscriptions?', 'Subscription summary', 'What are my recurring costs?'
    """
    try:
        uid = _user_id(config)
        subscriptions = get_subscription(uid, is_active=True)
        summary = get_subscription_summary(subscriptions)
        print(
            f"[tool output] {summary.active_count} active subscriptions, {summary.total_monthly_cost} monthly cost"
        )
        return summary
    except Exception as e:
        result = f"Error getting subscription summary: {e}"
        print(f"[tool output] {result}")
        return SubscriptionSummary(
            total_monthly_cost=0,
            active_count=0,
            by_category=[],
            next_due_dates=[],
        )


@tool
def compare_months_tool(
    month1: str,
    month2: str,
    currency: str | None = None,
    config: RunnableConfig = None,
) -> MonthComparison | str:
    """Compare spending between two months.

    Use when user asks: 'Compare this month to last month', 'How does September compare to August?'

    Pass the current month first (month1) and the reference month second
    (month2). month format: "YYYY-MM". If either month contains mixed
    currencies, a per-currency breakdown is returned instead of a comparison.
    """
    try:
        uid = _user_id(config)

        year1, month_num1 = map(int, month1.split("-"))
        expenses1 = _db_to_expense_results(
            get_expenses_for_month(uid, year1, month_num1, currency)
        )
        year2, month_num2 = map(int, month2.split("-"))
        expenses2 = _db_to_expense_results(
            get_expenses_for_month(uid, year2, month_num2, currency)
        )

        groups1 = _group_by_currency(expenses1)
        groups2 = _group_by_currency(expenses2)

        if len(groups1) > 1 or len(groups2) > 1:
            return (
                f"{month1}: {_mixed_currency_message(groups1) if groups1 else 'no expenses'}\n"
                f"{month2}: {_mixed_currency_message(groups2) if groups2 else 'no expenses'}\n"
                "A direct comparison is not valid across mixed currencies."
            )

        curr1 = next(iter(groups1), None)
        curr2 = next(iter(groups2), None)
        if curr1 and curr2 and curr1 != curr2:
            return (
                f"Cannot compare {month1} ({curr1}) with {month2} ({curr2}) — "
                "different currencies. Report each month separately or convert."
            )

        shared_currency = curr1 or curr2 or currency or "INR"
        summary1 = get_monthly_summary(expenses1, month1, shared_currency)
        summary2 = get_monthly_summary(expenses2, month2, shared_currency)

        comparison = compare_months(summary1, summary2)
        print(
            f"[tool output] Comparison: {comparison.total_change} change ({comparison.total_change_percentage}%)"
        )
        return comparison
    except Exception as e:
        result = f"Error comparing months: {e}"
        print(f"[tool output] {result}")
        empty_summary = MonthlySummary(
            month="",
            total_spent=0,
            total_transactions=0,
            average_transaction=0,
            top_category="N/A",
            top_merchant="N/A",
            currency=currency or "INR",
        )
        return MonthComparison(
            current_month=empty_summary,
            previous_month=empty_summary,
            total_change=0,
            total_change_percentage=0,
            top_category_change={},
        )


@tool
def get_spending_by_merchant_tool(
    month: str | None = None,
    top_n: int = 5,
    currency: str | None = None,
    config: RunnableConfig = None,
) -> list[dict] | str:
    """Get top merchants by spending.

    Use when user asks: 'Where do I spend the most?', 'Top merchants', 'Biggest expenses'

    month format: "YYYY-MM". currency filters to a single currency; omit for
    all currencies. Mixed-currency months return a per-currency note instead.
    """
    try:
        uid = _user_id(config)
        if month is None:
            month = date.today().strftime("%Y-%m")

        year, month_num = map(int, month.split("-"))
        expenses = _db_to_expense_results(
            get_expenses_for_month(uid, year, month_num, currency)
        )

        if not expenses:
            return []

        groups = _group_by_currency(expenses)
        if len(groups) > 1:
            return f"Top merchants for {month}: " + _mixed_currency_message(groups)

        merchants = get_spending_by_merchant(expenses, top_n)
        print(f"[tool output] {len(merchants)} top merchants found")
        return merchants
    except Exception as e:
        result = f"Error getting spending by merchant: {e}"
        print(f"[tool output] {result}")
        return []


@tool
def get_upcoming_bills_tool(
    days_ahead: int = 7, config: RunnableConfig = None
) -> list[dict]:
    """Get subscriptions due within the next N days, including overdue ones.

    Use when the user asks about bills coming up, what is due soon, or
    upcoming payments. Also use proactively before suggesting
    process_due_subscriptions_tool.
    """
    try:
        uid = _user_id(config)
        today = date.today()
        subscriptions = get_subscriptions_due_within(uid, within_days=days_ahead)
        result = [
            {
                "id": s.id,
                "merchant": s.merchant,
                "amount": float(s.amount),
                "currency": s.currency,
                "due_date": s.next_due_date.isoformat(),
                "frequency": _freq_str(s.frequency),
                "overdue": s.next_due_date < today,
            }
            for s in subscriptions
        ]
        print(f"[tool output] {len(result)} bill(s) due within {days_ahead} day(s)")
        return result
    except Exception as e:
        print(f"[tool output] Error fetching upcoming bills: {e}")
        return []


@tool
def process_due_subscriptions_tool(
    confirm: bool = False, config: RunnableConfig = None
) -> str:
    """Record expenses for subscriptions that are due, and advance their due dates.

    A subscription is due when next_due_date is today or earlier. For each one,
    an expense is created for every missed billing period, and next_due_date is
    advanced past today so nothing is recorded twice.

    Two-phase: call with confirm=false first to preview what would be recorded,
    show the preview to the user, and only call again with confirm=true after
    the user explicitly confirms.
    """
    try:
        uid = _user_id(config)
        today = date.today()
        due = get_due_subscriptions(uid, on_or_before=today)

        if not due:
            return "No subscriptions are due right now."

        if not confirm:
            lines = [
                f"  {s.merchant}: {s.currency} {float(s.amount):,.2f}"
                f" ({_freq_str(s.frequency)}), due {s.next_due_date}"
                + (" — OVERDUE" if s.next_due_date < today else "")
                for s in due
            ]
            return (
                "CONFIRMATION REQUIRED — these due subscriptions would be "
                "recorded as expenses (nothing recorded yet):\n"
                + "\n".join(lines)
                + "\nShow this preview to the user and ask for confirmation. "
                "If the user confirms, call process_due_subscriptions_tool "
                "again with confirm=true."
            )

        recorded = []
        for s in due:
            freq = _freq_str(s.frequency)
            period_date = s.next_due_date
            periods = 0
            while period_date <= today and periods < 1200:
                expense = ExpenseInput(
                    amount=float(s.amount),
                    currency=s.currency,
                    merchant=s.merchant,
                    category=s.category,
                    subcategory=s.subcategory,
                    date=period_date,
                    description=f"Subscription payment: {s.merchant}",
                )
                save_expense(uid, expense, subscription_id=s.id)
                period_date = advance_due_date(period_date, freq)
                periods += 1
            advance_subscription_due_date(uid, s.id, period_date)
            recorded.append(
                f"  {s.merchant}: recorded {periods} x {s.currency} "
                f"{float(s.amount):,.2f}, next due {period_date}"
            )

        result = (
            f"Recorded subscription expenses for {len(recorded)} subscription(s):\n"
            + "\n".join(recorded)
        )
        warnings = _budget_warnings(uid)
        if warnings:
            result += "\n" + "\n".join(warnings)
        print(f"[tool output] {result}")
        return result
    except Exception as e:
        result = f"Error processing due subscriptions: {e}"
        print(f"[tool output] {result}")
        return result


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
    get_upcoming_bills_tool,
    process_due_subscriptions_tool,
]
